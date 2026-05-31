from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import Board

SCHEMA_VERSION = 1


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
    def index_path(self) -> Path:
        return self.base / "index.json"

    # ---- board IO ---------------------------------------------------------
    def _board_path(self, board_id: str) -> Path:
        return self.boards_dir / f"{board_id}.json"

    def _atomic_write(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            # keep the last good copy before overwriting
            backup = path.with_suffix(path.suffix + ".bak")
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
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

    def save_board(self, board: Board) -> None:
        text = json.dumps(board.to_dict(), indent=2, ensure_ascii=False)
        self._atomic_write(self._board_path(board.id), text)

    def load_board(self, board_id: str) -> Board:
        path = self._board_path(board_id)
        if not path.exists():
            raise StoreError(f"Board file not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            backup = path.with_suffix(path.suffix + ".bak")
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
        return Board.from_dict(data)

    def delete_board(self, board_id: str) -> None:
        for suffix in (".json", ".json.bak"):
            p = self.boards_dir / f"{board_id}{suffix}"
            if p.exists():
                p.unlink()

    def board_exists(self, board_id: str) -> bool:
        return self._board_path(board_id).exists()

    # ---- index IO ---------------------------------------------------------
    def _default_index(self) -> dict[str, Any]:
        return {"version": SCHEMA_VERSION, "theme": "dark", "boards": []}

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
