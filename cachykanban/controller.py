from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .models import Board, Card, Column, Label, Project, new_id
from .store import Store, StoreError

DEFAULT_COLUMNS: tuple[str, ...] = ("Backlog", "In Progress", "Done")
DEFAULT_COLUMN_COLORS = {
    "Backlog": "#7c8596",
    "In Progress": "#6ea8fe",
    "Done": "#48bb78",
}
DEFAULT_LABELS: tuple[tuple[str, str], ...] = (
    ("bug", "#fc8181"),
    ("feature", "#68d391"),
    ("idea", "#6ea8fe"),
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Controller:
    """Qt-free application state manager.

    ``project`` is the persistence aggregate and ``board`` is the currently
    selected child. Every board/card mutation saves the complete project file.
    """

    def __init__(self, store: Store) -> None:
        self.store = store
        self.now: Callable[[], str] = _iso_now
        self.index: dict[str, Any] = {
            "version": 2,
            "theme": "dark",
            "projects": [],
            "active_project_id": None,
        }
        self.project: Project | None = None
        self.board: Board | None = None

    @property
    def summaries(self) -> list[dict[str, str]]:
        """Project summaries shown by the project selector."""
        return self.index.setdefault("projects", [])

    @property
    def board_summaries(self) -> list[dict[str, str]]:
        project = self.project
        return [board.summary() for board in project.boards] if project else []

    @property
    def active_project_id(self) -> str | None:
        value = self.index.get("active_project_id")
        return value if isinstance(value, str) and value else None

    @property
    def active_board_id(self) -> str | None:
        return self.board.id if self.board else None

    @property
    def theme_name(self) -> str:
        return self.index.get("theme", "dark")

    # ---- lifecycle --------------------------------------------------------
    def load(self) -> None:
        loaded = self.store.load_index()
        if not isinstance(loaded, dict):
            loaded = {}

        # v1 used index["boards"] and boards/<id>.json. Migration writes every
        # readable board into projects/<id>.json and leaves the source files.
        if isinstance(loaded.get("boards"), list) and not isinstance(
            loaded.get("projects"), list
        ):
            loaded = self.store.migrate_legacy_index(loaded)

        project_summaries = loaded.get("projects", [])
        if not isinstance(project_summaries, list):
            project_summaries = []
        valid: list[dict[str, str]] = []
        for summary in project_summaries:
            if not isinstance(summary, dict):
                continue
            project_id = summary.get("id")
            name = summary.get("name")
            color = summary.get("color")
            if not all(isinstance(value, str) and value for value in (project_id, name, color)):
                continue
            try:
                project = self.store.load_project(project_id)
            except StoreError:
                continue
            if not project.boards:
                continue
            valid.append({"id": project.id, "name": project.name, "color": project.color})

        self.index = {
            "version": 2,
            "theme": loaded.get("theme", "dark"),
            "projects": valid,
            "active_project_id": loaded.get("active_project_id"),
        }
        if not valid:
            project = self._new_default_project()
            self.project = project
            self.board = project.active_board
            self.store.save_project(project)
            self.index["projects"] = [project.summary()]
            self.index["active_project_id"] = project.id
            self._save_index()
            return

        preferred = self.active_project_id
        project_id = next(
            (summary["id"] for summary in valid if summary["id"] == preferred),
            valid[0]["id"],
        )
        self.open_project(project_id)

    def open_project(self, project_id: str, board_id: str | None = None) -> Project:
        project = self.store.load_project(project_id)
        if not project.boards:
            raise StoreError(f"Project {project_id} contains no boards")
        self.project = project
        self.board = project.find_board(board_id) if board_id else None
        self.board = self.board or project.active_board or project.boards[0]
        project.active_board_id = self.board.id
        self.index["active_project_id"] = project.id
        self._sync_project_summary(project)
        self._save_index()
        # Route selection through the same board-open path used by the board
        # selector. This keeps one canonical active-board transition and one
        # observable open operation for UI integrations.
        self.open_board(self.board.id)
        return project

    def open_board(self, board_id: str) -> Board:
        project = self._require_project()
        board = project.find_board(board_id)
        if board is None:
            # Board IDs are global, but accepting a board from another
            # project makes the controller API safe for integrations that
            # receive a board selection without a preceding project event.
            for summary in self.summaries:
                if summary["id"] == project.id:
                    continue
                try:
                    candidate = self.store.load_project(summary["id"])
                except StoreError:
                    continue
                board = candidate.find_board(board_id)
                if board is not None:
                    project = candidate
                    self.project = project
                    break
        if board is None:
            raise KeyError(board_id)
        self.board = board
        project.active_board_id = board.id
        project.updated = self.now()
        self.store.save_project(project)
        self.index["active_project_id"] = project.id
        self._save_index()
        return board

    def set_theme(self, theme: str) -> None:
        self.index["theme"] = theme
        self._save_index()

    # ---- projects ---------------------------------------------------------
    def add_project(self, name: str, color: str = "#6ea8fe") -> Project:
        project_id = new_id()
        board = self._new_board("My Board", color)
        # The initial board keeps the project id for v1 continuity. It is
        # still a child in the project aggregate and subsequent boards get
        # independent IDs.
        board.id = project_id
        project = Project(
            id=project_id, name=name, color=color, boards=[board],
            active_board_id=board.id, created=self.now(), updated=self.now(),
        )
        self.store.save_project(project)
        self.project, self.board = project, board
        self.summaries.append(project.summary())
        self.index["active_project_id"] = project.id
        self._save_index()
        return project

    def rename_project(self, project_id: str, name: str) -> None:
        project = self._project_by_id(project_id)
        project.name = name
        project.updated = self.now()
        self.store.save_project(project)
        self._sync_project_summary(project)
        self._save_index()

    def recolor_project(self, project_id: str, color: str) -> None:
        project = self._project_by_id(project_id)
        project.color = color
        project.updated = self.now()
        self.store.save_project(project)
        self._sync_project_summary(project)
        self._save_index()

    def delete_project(self, project_id: str) -> None:
        if not any(summary["id"] == project_id for summary in self.summaries):
            raise KeyError(project_id)
        if len(self.summaries) == 1:
            # Never leave a new install without something usable.
            replacement = self._new_default_project()
            self.store.delete_project(project_id)
            self.store.save_project(replacement)
            self.project, self.board = replacement, replacement.active_board
            self.index["projects"] = [replacement.summary()]
            self.index["active_project_id"] = replacement.id
            self._save_index()
            return
        self.store.delete_project(project_id)
        self.index["projects"] = [s for s in self.summaries if s["id"] != project_id]
        if self.active_project_id == project_id:
            self.project = self.board = None
            self.open_project(self.summaries[0]["id"])
        else:
            self._save_index()

    # ---- boards -----------------------------------------------------------
    def add_board(self, name: str, color: str = "#6ea8fe") -> Board:
        project = self._require_project()
        board = self._new_board(name, color)
        project.boards.append(board)
        project.active_board_id = board.id
        self.board = board
        self._persist()
        return board

    def rename_board(self, board_id: str, name: str) -> None:
        self._find_board(board_id).name = name
        self._persist()

    def recolor_board(self, board_id: str, color: str) -> None:
        self._find_board(board_id).color = color
        self._persist()

    def delete_board(self, board_id: str) -> None:
        project = self._require_project()
        if len(project.boards) <= 1:
            return
        if project.find_board(board_id) is None:
            raise KeyError(board_id)
        project.boards = [board for board in project.boards if board.id != board_id]
        if project.active_board_id == board_id:
            project.active_board_id = project.boards[0].id
            self.board = project.active_board
        self._persist()

    def reorder_boards(self, ordered_ids: list[str]) -> None:
        project = self._require_project()
        by_id = {board.id: board for board in project.boards}
        project.boards = [by_id[board_id] for board_id in ordered_ids if board_id in by_id]
        project.boards.extend(board for board in by_id.values() if board not in project.boards)
        self._persist()

    # ---- columns ----------------------------------------------------------
    def add_column(self, name: str, color: str = "#7c8596") -> Column:
        column = Column(id=new_id(), name=name, color=color)
        self._require_board().columns.append(column)
        self._persist()
        return column

    def rename_column(self, column_id: str, name: str) -> None:
        self._require_column(column_id).name = name
        self._persist()

    def recolor_column(self, column_id: str, color: str) -> None:
        self._require_column(column_id).color = color
        self._persist()

    def delete_column(self, column_id: str) -> None:
        board = self._require_board()
        board.columns = [column for column in board.columns if column.id != column_id]
        self._persist()

    def reorder_columns(self, ordered_ids: list[str]) -> None:
        board = self._require_board()
        by_id = {column.id: column for column in board.columns}
        board.columns = [by_id[column_id] for column_id in ordered_ids if column_id in by_id]
        board.columns.extend(column for column in by_id.values() if column not in board.columns)
        self._persist()

    # ---- cards ------------------------------------------------------------
    def add_card(self, column_id: str, title: str) -> Card:
        card = Card(id=new_id(), title=title, created=self.now(), updated=self.now())
        self._require_column(column_id).cards.append(card)
        self._persist()
        return card

    def update_card(self, card_id: str, **fields: Any) -> None:
        _, card = self._require_card(card_id)
        for key, value in fields.items():
            setattr(card, key, value)
        card.updated = self.now()
        self._persist()

    def set_card_archived(self, card_id: str, archived: bool) -> None:
        self.update_card(card_id, archived=archived)

    def delete_card(self, card_id: str) -> None:
        column, _ = self._require_card(card_id)
        column.cards = [card for card in column.cards if card.id != card_id]
        self._persist()

    def move_card(self, card_id: str, to_column_id: str, index: int) -> None:
        column, card = self._require_card(card_id)
        target = self._require_column(to_column_id)
        column.cards = [item for item in column.cards if item.id != card_id]
        index = max(0, min(index, len(target.cards)))
        target.cards.insert(index, card)
        self._persist()

    # ---- labels -----------------------------------------------------------
    def add_label(self, name: str, color: str) -> Label:
        label = Label(id=new_id(), name=name, color=color)
        self._require_board().labels.append(label)
        self._persist()
        return label

    def update_label(self, label_id: str, name: str, color: str) -> None:
        label = self._require_board().find_label(label_id)
        if label is None:
            raise KeyError(label_id)
        label.name, label.color = name, color
        self._persist()

    def delete_label(self, label_id: str) -> None:
        board = self._require_board()
        board.labels = [label for label in board.labels if label.id != label_id]
        for column in board.columns:
            for card in column.cards:
                card.label_ids = [item for item in card.label_ids if item != label_id]
        self._persist()

    # ---- internals --------------------------------------------------------
    def _new_board(self, name: str, color: str) -> Board:
        return Board(
            id=new_id(), name=name, color=color,
            columns=self._default_columns(), labels=self._default_labels(),
            created=self.now(), updated=self.now(),
        )

    def _new_default_project(self) -> Project:
        project_id = new_id()
        board = self._new_board("My Board", "#6ea8fe")
        board.id = project_id
        return Project(
            id=project_id, name="My Project", color="#6ea8fe", boards=[board],
            active_board_id=board.id, created=self.now(), updated=self.now(),
        )

    def _default_columns(self) -> list[Column]:
        return [Column(id=new_id(), name=name, color=DEFAULT_COLUMN_COLORS[name]) for name in DEFAULT_COLUMNS]

    def _default_labels(self) -> list[Label]:
        return [Label(id=new_id(), name=name, color=color) for name, color in DEFAULT_LABELS]

    def _project_by_id(self, project_id: str) -> Project:
        if self.project is not None and self.project.id == project_id:
            return self.project
        return self.store.load_project(project_id)

    def _find_board(self, board_id: str) -> Board:
        board = self._require_project().find_board(board_id)
        if board is None:
            raise KeyError(board_id)
        return board

    def _require_project(self) -> Project:
        if self.project is None:
            raise RuntimeError("No project is open")
        return self.project

    def _require_board(self) -> Board:
        if self.board is None:
            raise RuntimeError("No board is open")
        return self.board

    def _require_column(self, column_id: str) -> Column:
        column = self._require_board().find_column(column_id)
        if column is None:
            raise KeyError(column_id)
        return column

    def _require_card(self, card_id: str) -> tuple[Column, Card]:
        found = self._require_board().find_card(card_id)
        if found is None:
            raise KeyError(card_id)
        return found

    def _sync_project_summary(self, project: Project) -> None:
        for summary in self.summaries:
            if summary["id"] == project.id:
                summary.update(project.summary())
                return
        self.summaries.append(project.summary())

    def _persist(self) -> None:
        project = self._require_project()
        project.updated = self.now()
        if self.board is not None:
            project.active_board_id = self.board.id
            self.board.updated = self.now()
        self.store.save_project(project)
        self._sync_project_summary(project)
        self.index["active_project_id"] = project.id
        self._save_index()

    def _save_index(self) -> None:
        self.store.save_index(self.index)
