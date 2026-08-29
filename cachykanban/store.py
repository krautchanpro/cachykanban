from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import Board, Project

SCHEMA_VERSION = 2


class StoreError(Exception):
    """Raised when board data cannot be loaded or recovered."""


def default_base() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    root = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return root / "cachykanban"


class Store:
    def __init__(self, base: Path | None = None) -> None:
        self.base = Path(base) if base is not None else default_base()

    @property
    def boards_dir(self) -> Path:
        return self.base / "boards"

    @property
    def projects_dir(self) -> Path:
        return self.base / "projects"

    @property
    def index_path(self) -> Path:
        return self.base / "index.json"

    # ---- board IO ---------------------------------------------------------
    def _board_path(self, board_id: str) -> Path:
        return self.boards_dir / f"{board_id}.json"

    def _project_path(self, project_id: str) -> Path:
        return self.projects_dir / f"{project_id}.json"

    def _write_file_atomic(self, path: Path, text: str) -> None:
        """Write text to path atomically (temp file + fsync + os.replace)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

    def _atomic_write(self, path: Path, text: str) -> None:
        """Commit text to path, then mirror it to a sibling ``.bak``.

        The backup always holds the most recent good content, so if the main
        file is later truncated or corrupted, ``load_*`` recovers the latest
        save rather than a stale one.
        """
        self._write_file_atomic(path, text)
        backup = path.with_suffix(path.suffix + ".bak")
        self._write_file_atomic(backup, text)

    def save_board(self, board: Board) -> None:
        """Write a legacy board file.

        This method remains available only for importing/recovery of v1 data;
        the controller writes project aggregates with :meth:`save_project`.
        """
        text = json.dumps(board.to_dict(), indent=2, ensure_ascii=False)
        self._atomic_write(self._board_path(board.id), text)

    def load_board(self, board_id: str) -> Board:
        path = self._board_path(board_id)
        if not path.exists():
            raise StoreError(f"Board file not found: {path}")
        backup = path.with_suffix(path.suffix + ".bak")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            if backup.exists():
                try:
                    data = json.loads(backup.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc2:
                    raise StoreError(
                        f"Board {board_id} and its backup are unreadable: {exc2}"
                    ) from exc2
            else:
                raise StoreError(
                    f"Board {board_id} is corrupt and no backup exists: {exc}"
                ) from exc
        try:
            return Board.from_dict(data)
        except (AttributeError, TypeError, ValueError, KeyError) as exc:
            if backup.exists():
                try:
                    return Board.from_dict(json.loads(backup.read_text(encoding="utf-8")))
                except (json.JSONDecodeError, OSError, AttributeError, TypeError, ValueError, KeyError):
                    pass
            raise StoreError(f"Board {board_id} has invalid data") from exc

    def delete_board(self, board_id: str) -> None:
        for suffix in (".json", ".json.bak"):
            p = self.boards_dir / f"{board_id}{suffix}"
            if p.exists():
                p.unlink()

    def board_exists(self, board_id: str) -> bool:
        if self._board_path(board_id).exists():
            return True
        # Compatibility for callers that used board_exists as a storage
        # assertion before projects became the persistence boundary.
        if not self.projects_dir.exists():
            return False
        for path in self.projects_dir.glob("*.json"):
            try:
                project = Project.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
            if project.find_board(board_id) is not None:
                return True
        return False

    # ---- project IO -------------------------------------------------------
    def save_project(self, project: Project) -> None:
        text = json.dumps(project.to_dict(), indent=2, ensure_ascii=False)
        self._atomic_write(self._project_path(project.id), text)

    def load_project(self, project_id: str) -> Project:
        path = self._project_path(project_id)
        if not path.exists():
            raise StoreError(f"Project file not found: {path}")
        backup = path.with_suffix(path.suffix + ".bak")
        data: Any
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            if backup.exists():
                try:
                    data = json.loads(backup.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc2:
                    raise StoreError(
                        f"Project {project_id} and its backup are unreadable: {exc2}"
                    ) from exc2
            else:
                raise StoreError(
                    f"Project {project_id} is corrupt and no backup exists: {exc}"
                ) from exc
        if not isinstance(data, dict):
            raise StoreError(f"Project {project_id} has invalid JSON shape")
        try:
            return Project.from_dict(data)
        except (AttributeError, TypeError, ValueError, KeyError) as exc:
            if backup.exists():
                try:
                    return Project.from_dict(json.loads(backup.read_text(encoding="utf-8")))
                except (json.JSONDecodeError, OSError, AttributeError, TypeError, ValueError, KeyError):
                    pass
            raise StoreError(f"Project {project_id} has invalid data") from exc

    def delete_project(self, project_id: str) -> None:
        for suffix in (".json", ".json.bak"):
            path = self.projects_dir / f"{project_id}{suffix}"
            if path.exists():
                path.unlink()

    def project_exists(self, project_id: str) -> bool:
        return self._project_path(project_id).exists()

    # ---- index IO ---------------------------------------------------------
    def _default_index(self) -> dict[str, Any]:
        return {
            "version": SCHEMA_VERSION,
            "theme": "dark",
            "projects": [],
            "active_project_id": None,
        }

    def save_index(self, index: dict[str, Any]) -> None:
        text = json.dumps(index, indent=2, ensure_ascii=False)
        self._atomic_write(self.index_path, text)

    def load_index(self) -> dict[str, Any]:
        path = self.index_path
        if not path.exists():
            index = self._default_index()
            self.save_index(index)
            return index
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            backup = path.with_suffix(path.suffix + ".bak")
            if backup.exists():
                try:
                    return json.loads(backup.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            return self._default_index()

    def migrate_legacy_index(self, legacy: dict[str, Any]) -> dict[str, Any]:
        """Convert a v1 board-per-file index into project aggregates.

        Legacy board JSON files are deliberately never removed.  Project files
        and the new index are written only after every readable legacy board
        has been copied, making this operation safe to retry after interruption.
        """
        if not isinstance(legacy, dict):
            legacy = {}
        raw = legacy.get("boards", [])
        if not isinstance(raw, list):
            raw = []
        projects: list[Project] = []
        for summary in raw:
            if not isinstance(summary, dict):
                continue
            board_id = summary.get("id")
            if not isinstance(board_id, str) or not board_id:
                continue
            try:
                board = self.load_board(board_id)
            except StoreError:
                # A stale/corrupt entry must not prevent other boards from
                # migrating.  Its legacy file remains available for recovery.
                continue
            project = Project(
                id=board.id,
                name=str(summary.get("name") or board.name),
                color=str(summary.get("color") or board.color),
                boards=[board],
                active_board_id=board.id,
                created=board.created,
                updated=board.updated,
            )
            # Preserve a project already produced by a previous interrupted
            # migration if it is complete and readable.
            try:
                existing = self.load_project(project.id)
            except StoreError:
                existing = None
            if existing is not None and existing.find_board(board.id) is not None:
                project = existing
            projects.append(project)

        for project in projects:
            self.save_project(project)
        preferred = legacy.get("active_project_id", legacy.get("active_board_id"))
        active_id = preferred if isinstance(preferred, str) and any(
            project.id == preferred for project in projects
        ) else (projects[0].id if projects else None)
        migrated = {
            "version": SCHEMA_VERSION,
            "theme": legacy.get("theme", "dark"),
            "projects": [project.summary() for project in projects],
            "active_project_id": active_id,
        }
        # Project files are durable before this index replaces the old one.
        self.save_index(migrated)
        return migrated
