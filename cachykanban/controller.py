from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .models import Board, Card, Column, Label, new_id
from .store import Store, StoreError

DEFAULT_COLUMNS: tuple[str, ...] = ("Backlog", "In Progress", "Done")
DEFAULT_COLUMN_COLORS = {"Backlog": "#7c8596", "In Progress": "#6ea8fe", "Done": "#48bb78"}
DEFAULT_LABELS: tuple[tuple[str, str], ...] = (
    ("bug", "#fc8181"),
    ("feature", "#68d391"),
    ("idea", "#6ea8fe"),
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Controller:
    """The only object that mutates board state and persists it. Qt-free."""

    def __init__(self, store: Store) -> None:
        self.store = store
        self.now: Callable[[], str] = _iso_now
        self.index: dict[str, Any] = {
            "version": 1,
            "theme": "dark",
            "boards": [],
            "active_project_id": None,
        }
        self.board: Board | None = None

    # ---- properties -------------------------------------------------------
    @property
    def summaries(self) -> list[dict[str, str]]:
        return self.index["boards"]

    @property
    def active_project_id(self) -> str | None:
        """The last project opened, if it still refers to a known board."""
        value = self.index.get("active_project_id")
        return value if isinstance(value, str) else None

    @property
    def theme_name(self) -> str:
        return self.index.get("theme", "dark")

    # ---- lifecycle --------------------------------------------------------
    def load(self) -> None:
        loaded = self.store.load_index()
        # Older index files do not have active_project_id.  Keep their board
        # summaries, while filtering malformed/stale entries so a bad index
        # cannot prevent the app from starting.
        if not isinstance(loaded, dict):
            loaded = {}
        summaries = loaded.get("boards", [])
        if not isinstance(summaries, list):
            summaries = []
        valid_summaries: list[dict[str, str]] = []
        for summary in summaries:
            if not isinstance(summary, dict):
                continue
            board_id = summary.get("id")
            name = summary.get("name")
            color = summary.get("color")
            if not all(isinstance(value, str) and value for value in (board_id, name, color)):
                continue
            try:
                self.store.load_board(board_id)
            except StoreError:
                # Leave unreadable board files untouched; omit only their
                # stale index entries and fall back to another board/default.
                continue
            valid_summaries.append({"id": board_id, "name": name, "color": color})
        self.index = {
            "version": loaded.get("version", 1),
            "theme": loaded.get("theme", "dark"),
            "boards": valid_summaries,
            "active_project_id": loaded.get(
                "active_project_id", loaded.get("active_board_id")
            ),
        }
        if not self.summaries:
            board = self._new_default_board()
            self.summaries.append(board.summary())
            self.store.save_board(board)
            self.index["active_project_id"] = board.id
            self._save_index()
            self.board = board
        else:
            preferred = self.active_project_id
            board_id = next(
                (
                    summary["id"]
                    for summary in self.summaries
                    if summary["id"] == preferred
                ),
                self.summaries[0]["id"],
            )
            self.open_board(board_id)

    def open_board(self, board_id: str) -> Board:
        self.board = self.store.load_board(board_id)
        self.index["active_project_id"] = board_id
        self._save_index()
        return self.board

    # Project terminology is exposed alongside the original board API so
    # callers can adopt the UI language without breaking existing clients.
    def open_project(self, project_id: str) -> Board:
        return self.open_board(project_id)

    def set_theme(self, theme: str) -> None:
        self.index["theme"] = theme
        self._save_index()

    # ---- boards -----------------------------------------------------------
    def add_board(self, name: str, color: str) -> Board:
        board = Board(id=new_id(), name=name, color=color,
                      columns=self._default_columns(), labels=self._default_labels(),
                      created=self.now(), updated=self.now())
        self.summaries.append(board.summary())
        self.store.save_board(board)
        self._save_index()
        return board

    def add_project(self, name: str, color: str = "#6ea8fe") -> Board:
        return self.add_board(name, color)

    def rename_board(self, board_id: str, name: str) -> None:
        self._summary(board_id)["name"] = name
        if self.board and self.board.id == board_id:
            self.board.name = name
            self._persist()
        self._save_index()

    def recolor_board(self, board_id: str, color: str) -> None:
        self._summary(board_id)["color"] = color
        if self.board and self.board.id == board_id:
            self.board.color = color
            self._persist()
        self._save_index()

    def delete_board(self, board_id: str) -> None:
        self.index["boards"] = [s for s in self.summaries if s["id"] != board_id]
        self.store.delete_board(board_id)
        self._save_index()
        if self.board and self.board.id == board_id:
            self.board = None
            if self.summaries:
                self.open_board(self.summaries[0]["id"])
            else:
                self.index["active_project_id"] = None
                self._save_index()

    def reorder_boards(self, ordered_ids: list[str]) -> None:
        by_id = {s["id"]: s for s in self.summaries}
        self.index["boards"] = [by_id[i] for i in ordered_ids if i in by_id]
        self._save_index()

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
        board.columns = [c for c in board.columns if c.id != column_id]
        self._persist()

    def reorder_columns(self, ordered_ids: list[str]) -> None:
        board = self._require_board()
        by_id = {c.id: c for c in board.columns}
        board.columns = [by_id[i] for i in ordered_ids if i in by_id]
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
        column, card = self._require_card(card_id)
        column.cards = [c for c in column.cards if c.id != card_id]
        self._persist()

    def move_card(self, card_id: str, to_column_id: str, index: int) -> None:
        column, card = self._require_card(card_id)
        target = self._require_column(to_column_id)
        column.cards = [c for c in column.cards if c.id != card_id]
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
        label.name = name
        label.color = color
        self._persist()

    def delete_label(self, label_id: str) -> None:
        board = self._require_board()
        board.labels = [l for l in board.labels if l.id != label_id]
        for column in board.columns:
            for card in column.cards:
                if label_id in card.label_ids:
                    card.label_ids = [x for x in card.label_ids if x != label_id]
        self._persist()

    # ---- internals --------------------------------------------------------
    def _new_default_board(self) -> Board:
        return Board(id=new_id(), name="My Board", color="#6ea8fe",
                     columns=self._default_columns(), labels=self._default_labels(),
                     created=self.now(), updated=self.now())

    def _default_columns(self) -> list[Column]:
        return [Column(id=new_id(), name=name, color=DEFAULT_COLUMN_COLORS[name])
                for name in DEFAULT_COLUMNS]

    def _default_labels(self) -> list[Label]:
        return [Label(id=new_id(), name=name, color=color) for name, color in DEFAULT_LABELS]

    def _summary(self, board_id: str) -> dict[str, str]:
        for s in self.summaries:
            if s["id"] == board_id:
                return s
        raise KeyError(board_id)

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

    def _persist(self) -> None:
        board = self._require_board()
        board.updated = self.now()
        self.store.save_board(board)
        # keep the summary's name/color in sync
        try:
            summary = self._summary(board.id)
            summary["name"] = board.name
            summary["color"] = board.color
            self._save_index()
        except KeyError:
            pass

    def _save_index(self) -> None:
        self.store.save_index(self.index)
