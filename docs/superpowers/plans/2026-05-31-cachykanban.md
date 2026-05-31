# CachyKanban Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build CachyKanban — a fast, offline, native PySide6/Qt Kanban desktop app for Arch Linux with multiple boards, customizable columns, and customizable cards.

**Architecture:** Pure, Qt-free logic (`models.py`, `store.py`, `search.py`, `controller.py`) is unit-tested in isolation; thin Qt widgets under `ui/` render model state and call the controller; the controller is the single place that mutates the model and persists it. Storage is atomic JSON-per-board under `~/.local/share/cachykanban/` with `.bak` recovery.

**Tech Stack:** Python ≥3.11, PySide6/Qt Widgets, JSON persistence, `unittest` tests, setuptools + Arch PKGBUILD packaging. Mirrors the sibling `godot-plugin-updater` project conventions.

**Spec:** `docs/superpowers/specs/2026-05-31-cachykanban-design.md`

---

## Conventions for every task

- Project root: `/home/tubbyhubby/Projects/cachykanban`
- Run Python and tools through the project venv created in Task 1: `.venv/bin/python`, `.venv/bin/pip`.
- Run all commands from the project root.
- Tests use `unittest`; run a module with `.venv/bin/python -m unittest tests.test_x -v` and a single case with `.venv/bin/python -m unittest tests.test_x.ClassName.test_method -v`.
- IDs are random (`uuid4().hex[:8]`); tests never assert literal IDs — they construct objects with explicit IDs or capture the returned object's `.id`.

## File Structure (decided up front)

```
cachykanban/
  __init__.py          # __version__
  app.py               # QApplication bootstrap + main()
  __main__.py          # python -m cachykanban entry
  models.py            # PURE dataclasses (no Qt)
  store.py             # PURE persistence (no Qt)
  search.py            # PURE filter/sort (no Qt)
  controller.py        # PURE mutation+persistence mediator (no Qt)
  ui/
    __init__.py        # re-exports MainWindow
    theme.py           # QSS strings (no Qt import needed)
    card_widget.py     # one card face + drag source
    column_widget.py   # one column + card drop target
    board_view.py      # columns area + column drag-reorder
    sidebar.py         # board list
    card_editor.py     # modal card editor dialog
    label_manager.py   # board label palette dialog
    main_window.py     # sidebar + board area + search + shortcuts
tests/
  __init__.py
  test_models.py
  test_store.py
  test_search.py
  test_controller.py
  test_theme.py
  test_smoke.py
data/
  cachykanban          # launcher shim
  io.github.tubbyhubby.CachyKanban.desktop
  cachykanban.svg
packaging/arch/PKGBUILD
pyproject.toml
README.md
```

---

## Task 1: Scaffold project, venv, and package skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `cachykanban/__init__.py`
- Create: `cachykanban/ui/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "cachykanban"
version = "0.1.0"
description = "Offline native Kanban board for Arch Linux (PySide6/Qt)."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [
  { name = "tubbyhubby" }
]
dependencies = [
  "PySide6>=6.6"
]

[project.gui-scripts]
cachykanban = "cachykanban.app:main"

[tool.setuptools]
packages = ["cachykanban", "cachykanban.ui"]
```

- [ ] **Step 2: Create the package init files**

`cachykanban/__init__.py`:

```python
"""CachyKanban — offline native Kanban board for Arch Linux."""

__version__ = "0.1.0"
```

`cachykanban/ui/__init__.py` (placeholder for now; re-exports added in Task 18):

```python
"""CachyKanban Qt UI package."""
```

`tests/__init__.py`:

```python
```

- [ ] **Step 3: Create the venv (system PySide6) and install the package editable**

Run:
```bash
python -m venv --system-site-packages .venv
.venv/bin/pip install -e .
```
Expected: install completes; if system `pyside6` is present the `PySide6>=6.6` requirement is satisfied without a large download. If pip tries to build PySide6 and you'd rather use the system package only, confirm `pyside6` is installed via pacman and re-run.

- [ ] **Step 4: Verify imports work**

Run:
```bash
.venv/bin/python -c "import cachykanban; print(cachykanban.__version__)"
```
Expected: `0.1.0`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml cachykanban/ tests/__init__.py
git commit -m "chore: scaffold cachykanban package and venv"
```

---

## Task 2: Models — `ChecklistItem` and `Label`

**Files:**
- Create: `cachykanban/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:

```python
import unittest

from cachykanban.models import ChecklistItem, Label, new_id, PRIORITIES


class HelperTests(unittest.TestCase):
    def test_new_id_is_unique_hex(self):
        a, b = new_id(), new_id()
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), 8)
        int(a, 16)  # raises if not hex

    def test_priorities_constant(self):
        self.assertEqual(PRIORITIES, ("none", "low", "med", "high"))


class ChecklistItemTests(unittest.TestCase):
    def test_round_trip(self):
        item = ChecklistItem(text="write tests", done=True)
        self.assertEqual(ChecklistItem.from_dict(item.to_dict()), item)

    def test_from_dict_defaults(self):
        item = ChecklistItem.from_dict({})
        self.assertEqual(item.text, "")
        self.assertFalse(item.done)


class LabelTests(unittest.TestCase):
    def test_round_trip(self):
        label = Label(id="lbl12345", name="bug", color="#fc8181")
        self.assertEqual(Label.from_dict(label.to_dict()), label)

    def test_from_dict_generates_id_when_missing(self):
        label = Label.from_dict({"name": "idea", "color": "#6ea8fe"})
        self.assertTrue(label.id)
        self.assertEqual(label.name, "idea")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_models -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cachykanban.models'`

- [ ] **Step 3: Write minimal implementation**

`cachykanban/models.py`:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

PRIORITIES: tuple[str, ...] = ("none", "low", "med", "high")


def new_id() -> str:
    """Short, unique identifier for boards/columns/cards/labels."""
    return uuid.uuid4().hex[:8]


@dataclass(slots=True)
class ChecklistItem:
    text: str
    done: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "done": self.done}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChecklistItem":
        return cls(text=str(data.get("text", "")), done=bool(data.get("done", False)))


@dataclass(slots=True)
class Label:
    id: str
    name: str
    color: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "color": self.color}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Label":
        return cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name", "")),
            color=str(data.get("color", "#888888")),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_models -v`
Expected: PASS (5 tests OK)

- [ ] **Step 5: Commit**

```bash
git add cachykanban/models.py tests/test_models.py
git commit -m "feat: add ChecklistItem and Label models"
```

---

## Task 3: Models — `Card` with progress helper

**Files:**
- Modify: `cachykanban/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Add the failing test (append to `tests/test_models.py` before the `if __name__` line)**

```python
class CardTests(unittest.TestCase):
    def _card(self):
        from cachykanban.models import Card
        return Card(
            id="card0001",
            title="NPC idle animation",
            notes="wire into AnimationTree",
            label_ids=["lbl1", "lbl2"],
            checklist=[ChecklistItem("a", True), ChecklistItem("b", False)],
            priority="high",
            created="2026-05-31T00:00:00",
            updated="2026-05-31T00:00:00",
        )

    def test_round_trip(self):
        card = self._card()
        from cachykanban.models import Card
        self.assertEqual(Card.from_dict(card.to_dict()), card)

    def test_progress_counts_done_over_total(self):
        self.assertEqual(self._card().progress(), (1, 2))

    def test_progress_empty_checklist(self):
        from cachykanban.models import Card
        self.assertEqual(Card(id="c", title="t").progress(), (0, 0))

    def test_from_dict_clamps_unknown_priority_to_none(self):
        from cachykanban.models import Card
        card = Card.from_dict({"id": "c", "title": "t", "priority": "bogus"})
        self.assertEqual(card.priority, "none")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_models.CardTests -v`
Expected: FAIL — `ImportError: cannot import name 'Card'`

- [ ] **Step 3: Add `Card` to `cachykanban/models.py` (after `Label`)**

```python
@dataclass(slots=True)
class Card:
    id: str
    title: str
    notes: str = ""
    label_ids: list[str] = field(default_factory=list)
    checklist: list[ChecklistItem] = field(default_factory=list)
    priority: str = "none"
    archived: bool = False
    created: str = ""
    updated: str = ""

    def progress(self) -> tuple[int, int]:
        done = sum(1 for item in self.checklist if item.done)
        return done, len(self.checklist)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "notes": self.notes,
            "label_ids": list(self.label_ids),
            "checklist": [item.to_dict() for item in self.checklist],
            "priority": self.priority,
            "archived": self.archived,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Card":
        priority = str(data.get("priority", "none"))
        if priority not in PRIORITIES:
            priority = "none"
        return cls(
            id=str(data.get("id") or new_id()),
            title=str(data.get("title", "")),
            notes=str(data.get("notes", "")),
            label_ids=[str(x) for x in data.get("label_ids", [])],
            checklist=[ChecklistItem.from_dict(x) for x in data.get("checklist", [])],
            priority=priority,
            archived=bool(data.get("archived", False)),
            created=str(data.get("created", "")),
            updated=str(data.get("updated", "")),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_models -v`
Expected: PASS (9 tests OK)

- [ ] **Step 5: Commit**

```bash
git add cachykanban/models.py tests/test_models.py
git commit -m "feat: add Card model with checklist progress"
```

---

## Task 4: Models — `Column` and `Board` with lookup helpers

**Files:**
- Modify: `cachykanban/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Add the failing test (append before `if __name__`)**

```python
class BoardTests(unittest.TestCase):
    def _board(self):
        from cachykanban.models import Board, Column, Card, Label
        return Board(
            id="brd00001",
            name="SeedsOfAdventure",
            color="#6ea8fe",
            columns=[
                Column(id="col1", name="Backlog", color="#7c8596",
                       cards=[Card(id="c1", title="one")]),
                Column(id="col2", name="Done", color="#48bb78",
                       cards=[Card(id="c2", title="two")]),
            ],
            labels=[Label(id="l1", name="bug", color="#fc8181")],
        )

    def test_round_trip(self):
        from cachykanban.models import Board
        board = self._board()
        self.assertEqual(Board.from_dict(board.to_dict()), board)

    def test_find_column(self):
        board = self._board()
        self.assertEqual(board.find_column("col2").name, "Done")
        self.assertIsNone(board.find_column("nope"))

    def test_find_card_returns_column_and_card(self):
        board = self._board()
        col, card = board.find_card("c2")
        self.assertEqual(col.id, "col2")
        self.assertEqual(card.title, "two")

    def test_find_card_missing_returns_none(self):
        self.assertIsNone(self._board().find_card("ghost"))

    def test_summary(self):
        self.assertEqual(
            self._board().summary(),
            {"id": "brd00001", "name": "SeedsOfAdventure", "color": "#6ea8fe"},
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_models.BoardTests -v`
Expected: FAIL — `ImportError: cannot import name 'Column'`

- [ ] **Step 3: Add `Column` and `Board` to `cachykanban/models.py` (after `Card`)**

```python
@dataclass(slots=True)
class Column:
    id: str
    name: str
    color: str = "#7c8596"
    cards: list[Card] = field(default_factory=list)

    def find_card(self, card_id: str) -> Card | None:
        for card in self.cards:
            if card.id == card_id:
                return card
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "cards": [card.to_dict() for card in self.cards],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Column":
        return cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name", "")),
            color=str(data.get("color", "#7c8596")),
            cards=[Card.from_dict(x) for x in data.get("cards", [])],
        )


@dataclass(slots=True)
class Board:
    id: str
    name: str
    color: str = "#6ea8fe"
    columns: list[Column] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)
    created: str = ""
    updated: str = ""

    def find_column(self, column_id: str) -> Column | None:
        for column in self.columns:
            if column.id == column_id:
                return column
        return None

    def find_card(self, card_id: str) -> tuple[Column, Card] | None:
        for column in self.columns:
            card = column.find_card(card_id)
            if card is not None:
                return column, card
        return None

    def find_label(self, label_id: str) -> Label | None:
        for label in self.labels:
            if label.id == label_id:
                return label
        return None

    def summary(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "color": self.color}

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "columns": [column.to_dict() for column in self.columns],
            "labels": [label.to_dict() for label in self.labels],
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Board":
        return cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name", "")),
            color=str(data.get("color", "#6ea8fe")),
            columns=[Column.from_dict(x) for x in data.get("columns", [])],
            labels=[Label.from_dict(x) for x in data.get("labels", [])],
            created=str(data.get("created", "")),
            updated=str(data.get("updated", "")),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_models -v`
Expected: PASS (14 tests OK)

- [ ] **Step 5: Commit**

```bash
git add cachykanban/models.py tests/test_models.py
git commit -m "feat: add Column and Board models with lookup helpers"
```

---

## Task 5: Store — paths honoring XDG

**Files:**
- Create: `cachykanban/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

`tests/test_store.py`:

```python
import json
import os
import tempfile
import unittest
from pathlib import Path

from cachykanban.store import Store, StoreError, SCHEMA_VERSION
from cachykanban.models import Board, Column, Card


class PathTests(unittest.TestCase):
    def test_base_defaults_under_data_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["XDG_DATA_HOME"] = tmp
            store = Store()
            self.assertEqual(store.base, Path(tmp) / "cachykanban")
            del os.environ["XDG_DATA_HOME"]

    def test_explicit_base_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(base=Path(tmp) / "kb")
            self.assertEqual(store.base, Path(tmp) / "kb")
            self.assertEqual(store.boards_dir, Path(tmp) / "kb" / "boards")
            self.assertEqual(store.index_path, Path(tmp) / "kb" / "index.json")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_store.PathTests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cachykanban.store'`

- [ ] **Step 3: Write minimal implementation**

`cachykanban/store.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_store.PathTests -v`
Expected: PASS (2 tests OK)

- [ ] **Step 5: Commit**

```bash
git add cachykanban/store.py tests/test_store.py
git commit -m "feat: add Store path resolution honoring XDG_DATA_HOME"
```

---

## Task 6: Store — atomic board save/load with `.bak` recovery

**Files:**
- Modify: `cachykanban/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Add the failing test (append before `if __name__`)**

```python
class BoardIOTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(base=Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def _board(self):
        return Board(id="b1", name="B", color="#fff",
                     columns=[Column(id="c1", name="Todo", cards=[Card(id="k1", title="x")])])

    def test_save_then_load_round_trips(self):
        board = self._board()
        self.store.save_board(board)
        self.assertEqual(self.store.load_board("b1"), board)

    def test_save_writes_no_leftover_tmp_file(self):
        self.store.save_board(self._board())
        leftovers = list(self.store.boards_dir.glob("*.tmp"))
        self.assertEqual(leftovers, [])

    def test_second_save_creates_bak_of_previous(self):
        self.store.save_board(self._board())
        self.store.save_board(self._board())
        self.assertTrue((self.store.boards_dir / "b1.json.bak").exists())

    def test_corrupt_file_recovers_from_bak(self):
        self.store.save_board(self._board())          # creates b1.json
        self.store.save_board(self._board())          # creates b1.json.bak (good)
        path = self.store.boards_dir / "b1.json"
        path.write_text("{ this is not json", encoding="utf-8")
        recovered = self.store.load_board("b1")        # should fall back to .bak
        self.assertEqual(recovered.id, "b1")

    def test_corrupt_file_without_bak_raises_storeerror(self):
        self.store.save_board(self._board())
        (self.store.boards_dir / "b1.json").write_text("nonsense", encoding="utf-8")
        with self.assertRaises(StoreError):
            self.store.load_board("b1")

    def test_load_missing_board_raises_storeerror(self):
        with self.assertRaises(StoreError):
            self.store.load_board("ghost")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_store.BoardIOTests -v`
Expected: FAIL — `AttributeError: 'Store' object has no attribute 'save_board'`

- [ ] **Step 3: Add I/O methods to `cachykanban/store.py` (inside `Store`)**

```python
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
                    raise StoreError(f"Board {board_id} and its backup are unreadable: {exc2}") from exc2
            else:
                raise StoreError(f"Board {board_id} is corrupt and no backup exists: {exc}") from exc
        return Board.from_dict(data)

    def delete_board(self, board_id: str) -> None:
        for suffix in (".json", ".json.bak"):
            p = self.boards_dir / f"{board_id}{suffix}"
            if p.exists():
                p.unlink()

    def board_exists(self, board_id: str) -> bool:
        return self._board_path(board_id).exists()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_store.BoardIOTests -v`
Expected: PASS (6 tests OK)

- [ ] **Step 5: Commit**

```bash
git add cachykanban/store.py tests/test_store.py
git commit -m "feat: atomic board save/load with .bak corruption recovery"
```

---

## Task 7: Store — index (board order + theme) load/save

**Files:**
- Modify: `cachykanban/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Add the failing test (append before `if __name__`)**

```python
class IndexTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(base=Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_index_creates_default_when_missing(self):
        index = self.store.load_index()
        self.assertEqual(index["version"], SCHEMA_VERSION)
        self.assertEqual(index["theme"], "dark")
        self.assertEqual(index["boards"], [])

    def test_save_then_load_index(self):
        index = {"version": SCHEMA_VERSION, "theme": "light",
                 "boards": [{"id": "b1", "name": "B", "color": "#fff"}]}
        self.store.save_index(index)
        self.assertEqual(self.store.load_index(), index)

    def test_corrupt_index_recovers_from_bak(self):
        self.store.save_index({"version": SCHEMA_VERSION, "theme": "dark", "boards": []})
        self.store.save_index({"version": SCHEMA_VERSION, "theme": "light", "boards": []})
        self.store.index_path.write_text("broken", encoding="utf-8")
        self.assertEqual(self.store.load_index()["theme"], "light")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_store.IndexTests -v`
Expected: FAIL — `AttributeError: 'Store' object has no attribute 'load_index'`

- [ ] **Step 3: Add index methods to `cachykanban/store.py` (inside `Store`)**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_store -v`
Expected: PASS (11 tests OK across the store module)

- [ ] **Step 5: Commit**

```bash
git add cachykanban/store.py tests/test_store.py
git commit -m "feat: add index persistence with theme and board order"
```

---

## Task 8: Search — filter predicate and priority sort

**Files:**
- Create: `cachykanban/search.py`
- Test: `tests/test_search.py`

- [ ] **Step 1: Write the failing test**

`tests/test_search.py`:

```python
import unittest

from cachykanban.models import Card, Column
from cachykanban.search import card_matches, priority_rank, visible_cards


class CardMatchesTests(unittest.TestCase):
    def _card(self, **kw):
        defaults = dict(id="c", title="Fix nav bug", notes="repro in Blackmarsh",
                        label_ids=["l1"], priority="high")
        defaults.update(kw)
        return Card(**defaults)

    def test_empty_query_matches(self):
        self.assertTrue(card_matches(self._card()))

    def test_text_matches_title_case_insensitive(self):
        self.assertTrue(card_matches(self._card(), text="NAV"))

    def test_text_matches_notes(self):
        self.assertTrue(card_matches(self._card(), text="blackmarsh"))

    def test_text_no_match(self):
        self.assertFalse(card_matches(self._card(), text="zzz"))

    def test_label_filter(self):
        self.assertTrue(card_matches(self._card(), label_id="l1"))
        self.assertFalse(card_matches(self._card(), label_id="l2"))

    def test_priority_filter(self):
        self.assertTrue(card_matches(self._card(), priority="high"))
        self.assertFalse(card_matches(self._card(), priority="low"))


class PriorityRankTests(unittest.TestCase):
    def test_rank_order(self):
        self.assertEqual(priority_rank("high"), 3)
        self.assertEqual(priority_rank("none"), 0)
        self.assertGreater(priority_rank("med"), priority_rank("low"))


class VisibleCardsTests(unittest.TestCase):
    def test_excludes_archived_by_default(self):
        col = Column(id="c", name="x", cards=[
            Card(id="1", title="keep"),
            Card(id="2", title="gone", archived=True),
        ])
        ids = [c.id for c in visible_cards(col)]
        self.assertEqual(ids, ["1"])

    def test_include_archived_when_requested(self):
        col = Column(id="c", name="x", cards=[
            Card(id="1", title="keep"),
            Card(id="2", title="gone", archived=True),
        ])
        self.assertEqual(len(visible_cards(col, include_archived=True)), 2)

    def test_applies_text_filter_preserving_order(self):
        col = Column(id="c", name="x", cards=[
            Card(id="1", title="alpha"),
            Card(id="2", title="beta"),
            Card(id="3", title="alphabet"),
        ])
        self.assertEqual([c.id for c in visible_cards(col, text="alpha")], ["1", "3"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_search -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cachykanban.search'`

- [ ] **Step 3: Write minimal implementation**

`cachykanban/search.py`:

```python
from __future__ import annotations

from .models import Card, Column
from .models import PRIORITIES


def priority_rank(priority: str) -> int:
    try:
        return PRIORITIES.index(priority)
    except ValueError:
        return 0


def card_matches(
    card: Card,
    *,
    text: str = "",
    label_id: str | None = None,
    priority: str | None = None,
) -> bool:
    if text:
        needle = text.lower()
        if needle not in card.title.lower() and needle not in card.notes.lower():
            return False
    if label_id is not None and label_id not in card.label_ids:
        return False
    if priority is not None and card.priority != priority:
        return False
    return True


def visible_cards(
    column: Column,
    *,
    text: str = "",
    label_id: str | None = None,
    priority: str | None = None,
    include_archived: bool = False,
) -> list[Card]:
    result = []
    for card in column.cards:
        if card.archived and not include_archived:
            continue
        if card_matches(card, text=text, label_id=label_id, priority=priority):
            result.append(card)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_search -v`
Expected: PASS (12 tests OK)

- [ ] **Step 5: Commit**

```bash
git add cachykanban/search.py tests/test_search.py
git commit -m "feat: add card filter predicate and priority ranking"
```

---

## Task 9: Controller — load, boards, columns, cards, labels

**Files:**
- Create: `cachykanban/controller.py`
- Test: `tests/test_controller.py`

- [ ] **Step 1: Write the failing test**

`tests/test_controller.py`:

```python
import tempfile
import unittest
from pathlib import Path

from cachykanban.controller import Controller, DEFAULT_COLUMNS
from cachykanban.store import Store


def make_controller(tmp):
    store = Store(base=Path(tmp))
    controller = Controller(store)
    controller.now = lambda: "2026-05-31T12:00:00"  # deterministic timestamps
    controller.load()
    return controller


class LoadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp.cleanup()

    def test_first_load_creates_one_default_board(self):
        c = make_controller(self._tmp.name)
        self.assertEqual(len(c.summaries), 1)
        self.assertIsNotNone(c.board)
        self.assertEqual([col.name for col in c.board.columns], list(DEFAULT_COLUMNS))

    def test_reload_reopens_persisted_board(self):
        c = make_controller(self._tmp.name)
        first_id = c.board.id
        c.add_card(c.board.columns[0].id, "remember me")
        c2 = make_controller(self._tmp.name)
        self.assertEqual(c2.board.id, first_id)
        titles = [card.title for card in c2.board.columns[0].cards]
        self.assertIn("remember me", titles)


class MutationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.c = make_controller(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_board_appends_and_persists_summary(self):
        board = self.c.add_board("Second", "#48bb78")
        self.assertIn(board.id, [s["id"] for s in self.c.summaries])
        self.assertTrue(self.c.store.board_exists(board.id))

    def test_rename_and_recolor_board(self):
        bid = self.c.board.id
        self.c.rename_board(bid, "Renamed")
        self.c.recolor_board(bid, "#000000")
        summary = next(s for s in self.c.summaries if s["id"] == bid)
        self.assertEqual(summary["name"], "Renamed")
        self.assertEqual(summary["color"], "#000000")

    def test_delete_board_removes_file_and_summary(self):
        extra = self.c.add_board("Temp", "#fff")
        self.c.delete_board(extra.id)
        self.assertNotIn(extra.id, [s["id"] for s in self.c.summaries])
        self.assertFalse(self.c.store.board_exists(extra.id))

    def test_add_rename_delete_column(self):
        col = self.c.add_column("Review", "#b794f6")
        self.assertIn(col.id, [x.id for x in self.c.board.columns])
        self.c.rename_column(col.id, "QA")
        self.assertEqual(self.c.board.find_column(col.id).name, "QA")
        self.c.delete_column(col.id)
        self.assertIsNone(self.c.board.find_column(col.id))

    def test_add_card_sets_timestamps(self):
        col_id = self.c.board.columns[0].id
        card = self.c.add_card(col_id, "new task")
        self.assertEqual(card.created, "2026-05-31T12:00:00")
        self.assertEqual(card.updated, "2026-05-31T12:00:00")

    def test_update_card_changes_fields_and_updated(self):
        col_id = self.c.board.columns[0].id
        card = self.c.add_card(col_id, "task")
        self.c.update_card(card.id, title="edited", priority="high")
        _, fresh = self.c.board.find_card(card.id)
        self.assertEqual(fresh.title, "edited")
        self.assertEqual(fresh.priority, "high")

    def test_archive_card(self):
        col_id = self.c.board.columns[0].id
        card = self.c.add_card(col_id, "task")
        self.c.set_card_archived(card.id, True)
        _, fresh = self.c.board.find_card(card.id)
        self.assertTrue(fresh.archived)

    def test_delete_card(self):
        col_id = self.c.board.columns[0].id
        card = self.c.add_card(col_id, "task")
        self.c.delete_card(card.id)
        self.assertIsNone(self.c.board.find_card(card.id))

    def test_add_label_and_delete_removes_from_cards(self):
        col_id = self.c.board.columns[0].id
        card = self.c.add_card(col_id, "task")
        label = self.c.add_label("bug", "#fc8181")
        self.c.update_card(card.id, label_ids=[label.id])
        self.c.delete_label(label.id)
        self.assertNotIn(label, self.c.board.labels)
        _, fresh = self.c.board.find_card(card.id)
        self.assertEqual(fresh.label_ids, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_controller -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cachykanban.controller'`

- [ ] **Step 3: Write minimal implementation**

`cachykanban/controller.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .models import Board, Card, Column, Label, new_id
from .store import Store

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
        self.index: dict[str, Any] = {"version": 1, "theme": "dark", "boards": []}
        self.board: Board | None = None

    # ---- properties -------------------------------------------------------
    @property
    def summaries(self) -> list[dict[str, str]]:
        return self.index["boards"]

    @property
    def theme_name(self) -> str:
        return self.index.get("theme", "dark")

    # ---- lifecycle --------------------------------------------------------
    def load(self) -> None:
        self.index = self.store.load_index()
        if not self.summaries:
            board = self._new_default_board()
            self.summaries.append(board.summary())
            self.store.save_board(board)
            self._save_index()
            self.board = board
        else:
            self.open_board(self.summaries[0]["id"])

    def open_board(self, board_id: str) -> Board:
        self.board = self.store.load_board(board_id)
        return self.board

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_controller -v`
Expected: PASS (13 tests OK)

- [ ] **Step 5: Commit**

```bash
git add cachykanban/controller.py tests/test_controller.py
git commit -m "feat: add Controller for board/column/card/label mutations"
```

---

## Task 10: Controller — move_card reorder semantics (explicit coverage)

**Files:**
- Modify: `tests/test_controller.py`

- [ ] **Step 1: Add the failing test (append before `if __name__`)**

```python
class MoveCardTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.c = make_controller(self._tmp.name)
        self.col_a = self.c.board.columns[0].id
        self.col_b = self.c.board.columns[1].id
        self.k1 = self.c.add_card(self.col_a, "one").id
        self.k2 = self.c.add_card(self.col_a, "two").id
        self.k3 = self.c.add_card(self.col_a, "three").id

    def tearDown(self):
        self._tmp.cleanup()

    def _titles(self, col_id):
        return [card.title for card in self.c.board.find_column(col_id).cards]

    def test_reorder_within_column(self):
        self.c.move_card(self.k3, self.col_a, 0)
        self.assertEqual(self._titles(self.col_a), ["three", "one", "two"])

    def test_move_across_columns_at_index(self):
        self.c.move_card(self.k1, self.col_b, 0)
        self.assertEqual(self._titles(self.col_a), ["two", "three"])
        self.assertEqual(self._titles(self.col_b), ["one"])

    def test_index_is_clamped(self):
        self.c.move_card(self.k1, self.col_b, 999)
        self.assertEqual(self._titles(self.col_b), ["one"])
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `.venv/bin/python -m unittest tests.test_controller.MoveCardTests -v`
Expected: PASS (the `move_card` implemented in Task 9 already satisfies these). If any fail, fix `move_card` in `controller.py` so removal happens before clamping/insert, as written in Task 9.

- [ ] **Step 3: (No new implementation expected)**

If Step 2 passed, skip. If it failed, correct `move_card` per the Task 9 body and re-run.

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: PASS (all logic tests green)

- [ ] **Step 5: Commit**

```bash
git add tests/test_controller.py
git commit -m "test: cover move_card reorder and cross-column semantics"
```

---

## Task 11: Theme — QSS strings

**Files:**
- Create: `cachykanban/ui/theme.py`
- Test: `tests/test_theme.py`

- [ ] **Step 1: Write the failing test**

`tests/test_theme.py`:

```python
import unittest

from cachykanban.ui.theme import qss, palette, THEMES


class ThemeTests(unittest.TestCase):
    def test_themes_known(self):
        self.assertIn("dark", THEMES)
        self.assertIn("light", THEMES)

    def test_qss_nonempty_and_themeable(self):
        self.assertIn("QWidget", qss("dark"))
        self.assertNotEqual(qss("dark"), qss("light"))

    def test_unknown_theme_falls_back_to_dark(self):
        self.assertEqual(qss("bogus"), qss("dark"))

    def test_palette_has_core_keys(self):
        for key in ("bg", "panel", "ink", "accent", "line"):
            self.assertIn(key, palette("dark"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_theme -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cachykanban.ui.theme'`

- [ ] **Step 3: Write minimal implementation**

`cachykanban/ui/theme.py`:

```python
from __future__ import annotations

THEMES = ("dark", "light", "system")

_PALETTES = {
    "dark": {
        "bg": "#1b1d23", "panel": "#23262e", "panel2": "#2a2e38",
        "ink": "#e6e8ee", "sub": "#9aa3b2", "line": "#343945", "accent": "#6ea8fe",
    },
    "light": {
        "bg": "#f4f5f7", "panel": "#ffffff", "panel2": "#eef0f3",
        "ink": "#1b1d23", "sub": "#5a6473", "line": "#d6dae1", "accent": "#3b82f6",
    },
}


def palette(theme: str) -> dict[str, str]:
    if theme == "system":
        theme = "dark"
    return _PALETTES.get(theme, _PALETTES["dark"])


def qss(theme: str) -> str:
    p = palette(theme)
    return f"""
    QWidget {{ background: {p['bg']}; color: {p['ink']};
        font-family: "Inter", "Cantarell", system-ui, sans-serif; font-size: 13px; }}
    QFrame#Panel {{ background: {p['panel']}; border: 1px solid {p['line']};
        border-radius: 10px; }}
    QFrame#Card {{ background: {p['panel2']}; border: 1px solid {p['line']};
        border-radius: 8px; }}
    QFrame#Card:hover {{ border: 1px solid {p['accent']}; }}
    QLabel#ColumnTitle {{ font-weight: 700; }}
    QLabel#Muted {{ color: {p['sub']}; }}
    QPushButton {{ background: {p['panel2']}; border: 1px solid {p['line']};
        border-radius: 6px; padding: 5px 10px; }}
    QPushButton:hover {{ border: 1px solid {p['accent']}; }}
    QPushButton#Accent {{ background: {p['accent']}; color: #0c0d10; font-weight: 700; }}
    QLineEdit, QTextEdit, QComboBox {{ background: {p['panel']};
        border: 1px solid {p['line']}; border-radius: 6px; padding: 4px 6px; }}
    QListWidget {{ background: {p['panel']}; border: 1px solid {p['line']};
        border-radius: 8px; }}
    """
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_theme -v`
Expected: PASS (4 tests OK)

- [ ] **Step 5: Commit**

```bash
git add cachykanban/ui/theme.py tests/test_theme.py
git commit -m "feat: add dark/light QSS theme"
```

---

## Task 12: UI — `CardWidget` (face + drag source)

**Files:**
- Create: `cachykanban/ui/card_widget.py`

**Note:** Qt drag pixel-behavior is verified manually (Task 21). This task builds the widget and a constructor sanity check is exercised by the smoke test in Task 19.

- [ ] **Step 1: Implement `cachykanban/ui/card_widget.py`**

```python
from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QDrag, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..models import Board, Card
from ..search import priority_rank

CARD_MIME = "application/x-cachykanban-card"

_PRIORITY_COLOR = {"low": "#9aa3b2", "med": "#f6ad55", "high": "#fc8181"}


class CardWidget(QFrame):
    """One card. Click to edit; drag to move. Carries its card id in mime data."""

    clicked = Signal(str)  # card_id

    def __init__(self, card: Card, board: Board, column_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.card = card
        self.column_id = column_id
        self._press_pos = QPoint()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(6)

        if card.label_ids:
            chips = QHBoxLayout()
            chips.setSpacing(5)
            chips.setContentsMargins(0, 0, 0, 0)
            for label_id in card.label_ids:
                label = board.find_label(label_id)
                if label is None:
                    continue
                chip = QLabel(label.name)
                chip.setStyleSheet(
                    f"background:{label.color}; color:#0c0d10; border-radius:8px;"
                    "padding:1px 7px; font-size:11px; font-weight:600;"
                )
                chips.addWidget(chip)
            chips.addStretch(1)
            holder = QWidget()
            holder.setLayout(chips)
            layout.addWidget(holder)

        title = QLabel(card.title)
        title.setWordWrap(True)
        layout.addWidget(title)

        meta_bits = []
        done, total = card.progress()
        if total:
            meta_bits.append(f"☑ {done}/{total}")
        if card.priority != "none":
            color = _PRIORITY_COLOR.get(card.priority, "#9aa3b2")
            meta_bits.append(f"<span style='color:{color}'>⚑ {card.priority}</span>")
        if meta_bits:
            meta = QLabel("  ·  ".join(meta_bits))
            meta.setObjectName("Muted")
            meta.setTextFormat(Qt.TextFormat.RichText)
            meta.setStyleSheet("font-size:11px;")
            layout.addWidget(meta)

    # ---- interaction ------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            moved = (event.position().toPoint() - self._press_pos).manhattanLength()
            if moved < 6:
                self.clicked.emit(self.card.id)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self._press_pos).manhattanLength() < 12:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(CARD_MIME, self.card.id.encode("utf-8"))
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.exec(Qt.DropAction.MoveAction)
```

- [ ] **Step 2: Sanity-check the import compiles (offscreen)**

Run:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from cachykanban.ui.card_widget import CardWidget, CARD_MIME; print(CARD_MIME)"
```
Expected: `application/x-cachykanban-card`

- [ ] **Step 3: Commit**

```bash
git add cachykanban/ui/card_widget.py
git commit -m "feat: add CardWidget with click-to-edit and drag source"
```

---

## Task 13: UI — `ColumnWidget` (header actions + card drop target)

**Files:**
- Create: `cachykanban/ui/column_widget.py`

- [ ] **Step 1: Implement `cachykanban/ui/column_widget.py`**

```python
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QColorDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QMenu,
    QPushButton, QVBoxLayout, QWidget,
)

from ..controller import Controller
from ..models import Column
from .card_widget import CARD_MIME, CardWidget


class ColumnWidget(QFrame):
    """One column: header (name/color/count) + filtered card list + add-card."""

    cardClicked = Signal(str)       # card_id -> open editor
    changed = Signal()              # ask BoardView to rebuild

    def __init__(self, column: Column, controller: Controller, query: dict,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setAcceptDrops(True)
        self.column = column
        self.controller = controller
        self.query = query
        self.setFixedWidth(258)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        header = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{column.color};")
        title = QLabel(column.name)
        title.setObjectName("ColumnTitle")
        from ..search import visible_cards
        self._visible = visible_cards(
            column,
            text=query.get("text", ""),
            label_id=query.get("label_id"),
            priority=query.get("priority"),
        )
        count = QLabel(str(len(self._visible)))
        count.setObjectName("Muted")
        menu_btn = QPushButton("⋮")
        menu_btn.setFixedWidth(26)
        menu_btn.clicked.connect(self._open_menu)
        header.addWidget(dot)
        header.addWidget(title)
        header.addWidget(count)
        header.addStretch(1)
        header.addWidget(menu_btn)
        outer.addLayout(header)

        self._cards_box = QVBoxLayout()
        self._cards_box.setSpacing(8)
        self._cards_box.setContentsMargins(0, 0, 0, 0)
        for card in self._visible:
            widget = CardWidget(card, self.controller.board, column.id)
            widget.clicked.connect(self.cardClicked)
            self._cards_box.addWidget(widget)
        outer.addLayout(self._cards_box)

        add_btn = QPushButton("+ Add card")
        add_btn.clicked.connect(self._add_card)
        outer.addWidget(add_btn)
        outer.addStretch(1)

    # ---- header actions ---------------------------------------------------
    def _open_menu(self) -> None:
        menu = QMenu(self)
        rename = QAction("Rename column", self)
        rename.triggered.connect(self._rename)
        recolor = QAction("Change color", self)
        recolor.triggered.connect(self._recolor)
        delete = QAction("Delete column", self)
        delete.triggered.connect(self._delete)
        menu.addAction(rename)
        menu.addAction(recolor)
        menu.addSeparator()
        menu.addAction(delete)
        menu.exec(self.cursor().pos())

    def _rename(self) -> None:
        name, ok = QInputDialog.getText(self, "Rename column", "Name:", text=self.column.name)
        if ok and name.strip():
            self.controller.rename_column(self.column.id, name.strip())
            self.changed.emit()

    def _recolor(self) -> None:
        color = QColorDialog.getColor()
        if color.isValid():
            self.controller.recolor_column(self.column.id, color.name())
            self.changed.emit()

    def _delete(self) -> None:
        self.controller.delete_column(self.column.id)
        self.changed.emit()

    def _add_card(self) -> None:
        title, ok = QInputDialog.getText(self, "Add card", "Title:")
        if ok and title.strip():
            self.controller.add_card(self.column.id, title.strip())
            self.changed.emit()

    # ---- drop target ------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if not event.mimeData().hasFormat(CARD_MIME):
            return
        card_id = bytes(event.mimeData().data(CARD_MIME)).decode("utf-8")
        drop_y = event.position().toPoint().y()
        index = self._insertion_index(drop_y)
        self.controller.move_card(card_id, self.column.id, index)
        event.acceptProposedAction()
        self.changed.emit()

    def _insertion_index(self, drop_y: int) -> int:
        index = 0
        for i in range(self._cards_box.count()):
            item = self._cards_box.itemAt(i)
            widget = item.widget()
            if widget is None:
                continue
            center = widget.y() + widget.height() / 2
            if drop_y > center:
                index = i + 1
        return index
```

- [ ] **Step 2: Sanity-check it imports (offscreen)**

Run:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from cachykanban.ui.column_widget import ColumnWidget; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add cachykanban/ui/column_widget.py
git commit -m "feat: add ColumnWidget with header actions and card drop target"
```

---

## Task 14: UI — `BoardView` (columns area + add column)

**Files:**
- Create: `cachykanban/ui/board_view.py`

**Decision:** Column reordering for v1 is done via the column header menu using left/right moves is *not* used; instead BoardView exposes drag-reorder is deferred to a header drag handle in a later iteration. For v1 we ship **card** drag-and-drop (within and across columns, Task 13) and provide column reordering through `controller.reorder_columns` invoked by left/right actions added to the column menu. To honor the spec's "drag column headers," BoardView accepts a column-id mime drop on its background. This task implements the columns area, add-column, and the column-reorder drop.

- [ ] **Step 1: Add a column drag handle to `CardWidget`'s sibling — extend `ColumnWidget` header to be a column drag source**

Modify `cachykanban/ui/column_widget.py`: add the column mime constant and make the title draggable. Add near the top imports:

```python
from PySide6.QtCore import QMimeData, QPoint
from PySide6.QtGui import QDrag, QMouseEvent
```

Add this constant under the existing imports (top of file, after the `from .card_widget import ...` line):

```python
COLUMN_MIME = "application/x-cachykanban-column"
```

Then add these two methods to the `ColumnWidget` class (anywhere inside the class body):

```python
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._col_press = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        start = getattr(self, "_col_press", QPoint())
        if (event.position().toPoint() - start).manhattanLength() < 24:
            return
        # only start a column drag from the top header strip
        if event.position().toPoint().y() > 40:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(COLUMN_MIME, self.column.id.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
```

- [ ] **Step 2: Implement `cachykanban/ui/board_view.py`**

```python
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ..controller import Controller
from .column_widget import COLUMN_MIME, ColumnWidget


class BoardView(QScrollArea):
    """Horizontal area of columns for the current board. Rebuilds from model."""

    cardClicked = Signal(str)  # card_id

    def __init__(self, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.query: dict = {"text": "", "label_id": None, "priority": None}
        self.setWidgetResizable(True)
        self.setAcceptDrops(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.rebuild()

    def set_query(self, query: dict) -> None:
        self.query = query
        self.rebuild()

    def rebuild(self) -> None:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        board = self.controller.board
        if board is not None:
            for column in board.columns:
                col_widget = ColumnWidget(column, self.controller, self.query)
                col_widget.cardClicked.connect(self.cardClicked)
                col_widget.changed.connect(self.rebuild)
                row.addWidget(col_widget)

        add_col = QPushButton("+ Add column")
        add_col.setFixedWidth(140)
        add_col.clicked.connect(self._add_column)
        holder = QVBoxLayout()
        holder.addWidget(add_col)
        holder.addStretch(1)
        wrap = QWidget()
        wrap.setLayout(holder)
        row.addWidget(wrap)

        self.setWidget(container)

    def _add_column(self) -> None:
        name, ok = QInputDialog.getText(self, "Add column", "Name:")
        if ok and name.strip():
            self.controller.add_column(name.strip())
            self.rebuild()

    # ---- column reorder drop ---------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(COLUMN_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(COLUMN_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if not event.mimeData().hasFormat(COLUMN_MIME):
            return
        board = self.controller.board
        if board is None:
            return
        moved_id = bytes(event.mimeData().data(COLUMN_MIME)).decode("utf-8")
        drop_x = event.position().toPoint().x() + self.horizontalScrollBar().value()
        order = [c.id for c in board.columns if c.id != moved_id]
        insert_at = self._column_index_at(drop_x, exclude=moved_id)
        order.insert(insert_at, moved_id)
        self.controller.reorder_columns(order)
        event.acceptProposedAction()
        self.rebuild()

    def _column_index_at(self, drop_x: int, exclude: str) -> int:
        board = self.controller.board
        index = 0
        x = 16
        for column in board.columns:
            if column.id == exclude:
                continue
            col_width = 258 + 12
            if drop_x > x + col_width / 2:
                index += 1
            x += col_width
        return index
```

- [ ] **Step 3: Sanity-check imports (offscreen)**

Run:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from cachykanban.ui.board_view import BoardView; from cachykanban.ui.column_widget import COLUMN_MIME; print(COLUMN_MIME)"
```
Expected: `application/x-cachykanban-column`

- [ ] **Step 4: Commit**

```bash
git add cachykanban/ui/board_view.py cachykanban/ui/column_widget.py
git commit -m "feat: add BoardView with add-column and column drag-reorder"
```

---

## Task 15: UI — `Sidebar` (board list)

**Files:**
- Create: `cachykanban/ui/sidebar.py`

- [ ] **Step 1: Implement `cachykanban/ui/sidebar.py`**

```python
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QColorDialog, QInputDialog, QListWidget, QListWidgetItem, QMenu,
    QPushButton, QVBoxLayout, QWidget,
)

from ..controller import Controller


class Sidebar(QWidget):
    """Board list with add/rename/recolor/delete. Emits the selected board id."""

    boardSelected = Signal(str)
    changed = Signal()

    def __init__(self, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setFixedWidth(210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 6, 12)
        layout.setSpacing(8)

        self.list = QListWidget()
        self.list.itemClicked.connect(self._on_click)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list)

        add_btn = QPushButton("+ New board")
        add_btn.clicked.connect(self._add_board)
        layout.addWidget(add_btn)

        self.reload()

    def reload(self) -> None:
        self.list.clear()
        current_id = self.controller.board.id if self.controller.board else None
        for summary in self.controller.summaries:
            item = QListWidgetItem(summary["name"])
            item.setData(Qt.ItemDataRole.UserRole, summary["id"])
            self.list.addItem(item)
            if summary["id"] == current_id:
                self.list.setCurrentItem(item)

    def _on_click(self, item: QListWidgetItem) -> None:
        self.boardSelected.emit(item.data(Qt.ItemDataRole.UserRole))

    def _add_board(self) -> None:
        name, ok = QInputDialog.getText(self, "New board", "Name:")
        if ok and name.strip():
            board = self.controller.add_board(name.strip(), "#6ea8fe")
            self.reload()
            self.boardSelected.emit(board.id)

    def _on_context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        board_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        rename = QAction("Rename", self)
        rename.triggered.connect(lambda: self._rename(board_id, item.text()))
        recolor = QAction("Change color", self)
        recolor.triggered.connect(lambda: self._recolor(board_id))
        delete = QAction("Delete", self)
        delete.triggered.connect(lambda: self._delete(board_id))
        menu.addAction(rename)
        menu.addAction(recolor)
        menu.addSeparator()
        menu.addAction(delete)
        menu.exec(self.list.mapToGlobal(pos))

    def _rename(self, board_id: str, current: str) -> None:
        name, ok = QInputDialog.getText(self, "Rename board", "Name:", text=current)
        if ok and name.strip():
            self.controller.rename_board(board_id, name.strip())
            self.reload()
            self.changed.emit()

    def _recolor(self, board_id: str) -> None:
        color = QColorDialog.getColor()
        if color.isValid():
            self.controller.recolor_board(board_id, color.name())
            self.changed.emit()

    def _delete(self, board_id: str) -> None:
        self.controller.delete_board(board_id)
        self.reload()
        if self.controller.board:
            self.boardSelected.emit(self.controller.board.id)
        self.changed.emit()
```

- [ ] **Step 2: Sanity-check import (offscreen)**

Run:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from cachykanban.ui.sidebar import Sidebar; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add cachykanban/ui/sidebar.py
git commit -m "feat: add Sidebar board list with CRUD actions"
```

---

## Task 16: UI — `CardEditor` modal dialog

**Files:**
- Create: `cachykanban/ui/card_editor.py`

- [ ] **Step 1: Implement `cachykanban/ui/card_editor.py`**

```python
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTabWidget,
    QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from ..controller import Controller
from ..models import PRIORITIES, Card, ChecklistItem


class CardEditor(QDialog):
    """Modal editor for a single card. Applies changes via the controller."""

    def __init__(self, card_id: str, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.card_id = card_id
        found = controller.board.find_card(card_id)
        if found is None:
            raise KeyError(card_id)
        _, self.card = found
        self.setWindowTitle("Edit card")
        self.resize(460, 560)

        layout = QVBoxLayout(self)

        self.title_edit = QLineEdit(self.card.title)
        layout.addWidget(QLabel("Title"))
        layout.addWidget(self.title_edit)

        # notes with edit/preview tabs (Qt renders markdown natively)
        tabs = QTabWidget()
        self.notes_edit = QTextEdit(self.card.notes)
        preview = QTextBrowser()
        preview.setMarkdown(self.card.notes)
        self.notes_edit.textChanged.connect(lambda: preview.setMarkdown(self.notes_edit.toPlainText()))
        tabs.addTab(self.notes_edit, "Notes")
        tabs.addTab(preview, "Preview")
        layout.addWidget(QLabel("Notes (markdown)"))
        layout.addWidget(tabs)

        # priority
        prio_row = QHBoxLayout()
        prio_row.addWidget(QLabel("Priority"))
        self.priority_box = QComboBox()
        self.priority_box.addItems(PRIORITIES)
        self.priority_box.setCurrentText(self.card.priority)
        prio_row.addWidget(self.priority_box)
        prio_row.addStretch(1)
        layout.addLayout(prio_row)

        # labels as checkboxes
        layout.addWidget(QLabel("Labels"))
        self.label_boxes: list[tuple[str, QCheckBox]] = []
        labels_row = QHBoxLayout()
        for label in controller.board.labels:
            box = QCheckBox(label.name)
            box.setChecked(label.id in self.card.label_ids)
            self.label_boxes.append((label.id, box))
            labels_row.addWidget(box)
        labels_row.addStretch(1)
        layout.addLayout(labels_row)

        # checklist
        layout.addWidget(QLabel("Checklist"))
        self.checklist = QListWidget()
        for item in self.card.checklist:
            self._add_checklist_row(item.text, item.done)
        layout.addWidget(self.checklist)
        cl_row = QHBoxLayout()
        add_item = QPushButton("+ Add item")
        add_item.clicked.connect(self._add_checklist_item)
        rm_item = QPushButton("Remove selected")
        rm_item.clicked.connect(self._remove_checklist_item)
        cl_row.addWidget(add_item)
        cl_row.addWidget(rm_item)
        cl_row.addStretch(1)
        layout.addLayout(cl_row)

        # bottom: archive + ok/cancel
        bottom = QHBoxLayout()
        self.archive_btn = QPushButton("Unarchive" if self.card.archived else "Archive")
        self.archive_btn.clicked.connect(self._toggle_archive)
        bottom.addWidget(self.archive_btn)
        bottom.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)
        layout.addLayout(bottom)

    def _add_checklist_row(self, text: str, done: bool) -> None:
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if done else Qt.CheckState.Unchecked)
        self.checklist.addItem(item)

    def _add_checklist_item(self) -> None:
        text, ok = QInputDialog.getText(self, "Checklist item", "Text:")
        if ok and text.strip():
            self._add_checklist_row(text.strip(), False)

    def _remove_checklist_item(self) -> None:
        row = self.checklist.currentRow()
        if row >= 0:
            self.checklist.takeItem(row)

    def _toggle_archive(self) -> None:
        self.card.archived = not self.card.archived
        self.archive_btn.setText("Unarchive" if self.card.archived else "Archive")

    def _save(self) -> None:
        checklist = []
        for i in range(self.checklist.count()):
            item = self.checklist.item(i)
            checklist.append(ChecklistItem(item.text(), item.checkState() == Qt.CheckState.Checked))
        label_ids = [lid for lid, box in self.label_boxes if box.isChecked()]
        self.controller.update_card(
            self.card_id,
            title=self.title_edit.text().strip() or "Untitled",
            notes=self.notes_edit.toPlainText(),
            priority=self.priority_box.currentText(),
            label_ids=label_ids,
            checklist=checklist,
            archived=self.card.archived,
        )
        self.accept()
```

- [ ] **Step 2: Sanity-check import (offscreen)**

Run:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from cachykanban.ui.card_editor import CardEditor; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add cachykanban/ui/card_editor.py
git commit -m "feat: add modal CardEditor with notes/labels/checklist/priority"
```

---

## Task 17: UI — `LabelManager` dialog

**Files:**
- Create: `cachykanban/ui/label_manager.py`

- [ ] **Step 1: Implement `cachykanban/ui/label_manager.py`**

```python
from __future__ import annotations

from PySide6.QtWidgets import (
    QColorDialog, QDialog, QHBoxLayout, QInputDialog, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from ..controller import Controller


class LabelManager(QDialog):
    """Manage the current board's label palette (add / recolor / delete)."""

    def __init__(self, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Labels")
        self.resize(320, 380)

        layout = QVBoxLayout(self)
        self.list = QListWidget()
        layout.addWidget(self.list)

        add_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("New label name")
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add)
        add_row.addWidget(self.name_edit)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        actions = QHBoxLayout()
        recolor = QPushButton("Recolor selected")
        recolor.clicked.connect(self._recolor)
        delete = QPushButton("Delete selected")
        delete.clicked.connect(self._delete)
        actions.addWidget(recolor)
        actions.addWidget(delete)
        layout.addLayout(actions)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)

        self.reload()

    def reload(self) -> None:
        self.list.clear()
        for label in self.controller.board.labels:
            item = QListWidgetItem(label.name)
            item.setData(Qt.ItemDataRole.UserRole, label.id)
            item.setForeground(Qt.GlobalColor.black)
            item.setBackground(_qcolor(label.color))
            self.list.addItem(item)

    def _selected_id(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add(self) -> None:
        name = self.name_edit.text().strip()
        if name:
            self.controller.add_label(name, "#6ea8fe")
            self.name_edit.clear()
            self.reload()

    def _recolor(self) -> None:
        label_id = self._selected_id()
        if not label_id:
            return
        label = self.controller.board.find_label(label_id)
        color = QColorDialog.getColor()
        if color.isValid() and label is not None:
            self.controller.update_label(label_id, label.name, color.name())
            self.reload()

    def _delete(self) -> None:
        label_id = self._selected_id()
        if label_id:
            self.controller.delete_label(label_id)
            self.reload()


def _qcolor(hex_color: str):
    from PySide6.QtGui import QColor
    return QColor(hex_color)
```

- [ ] **Step 2: Sanity-check import (offscreen)**

Run:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from cachykanban.ui.label_manager import LabelManager; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add cachykanban/ui/label_manager.py
git commit -m "feat: add LabelManager dialog for board label palette"
```

---

## Task 18: UI — `MainWindow` (wiring, search bar, shortcuts) + package export

**Files:**
- Create: `cachykanban/ui/main_window.py`
- Modify: `cachykanban/ui/__init__.py`

- [ ] **Step 1: Implement `cachykanban/ui/main_window.py`**

```python
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLineEdit, QMainWindow, QPushButton, QWidget, QVBoxLayout,
)

from ..controller import Controller
from ..models import PRIORITIES
from . import theme
from .board_view import BoardView
from .card_editor import CardEditor
from .label_manager import LabelManager
from .sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("CachyKanban")
        self.resize(1180, 760)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar(controller)
        self.sidebar.boardSelected.connect(self._open_board)
        self.sidebar.changed.connect(self._refresh_board)
        root.addWidget(self.sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._build_toolbar())

        self.board_view = BoardView(controller)
        self.board_view.cardClicked.connect(self._edit_card)
        right_layout.addWidget(self.board_view)
        root.addWidget(right, 1)

        self.setCentralWidget(central)
        self._install_shortcuts()

    # ---- toolbar / search -------------------------------------------------
    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 6)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search cards…  (Ctrl+K)")
        self.search_edit.textChanged.connect(self._apply_query)
        layout.addWidget(self.search_edit, 1)

        self.priority_filter = QComboBox()
        self.priority_filter.addItem("Any priority", None)
        for p in PRIORITIES[1:]:
            self.priority_filter.addItem(p, p)
        self.priority_filter.currentIndexChanged.connect(self._apply_query)
        layout.addWidget(self.priority_filter)

        labels_btn = QPushButton("Labels…")
        labels_btn.clicked.connect(self._manage_labels)
        layout.addWidget(labels_btn)

        self.theme_box = QComboBox()
        self.theme_box.addItems(list(theme.THEMES))
        self.theme_box.setCurrentText(controller_theme(self.controller))
        self.theme_box.currentTextChanged.connect(self._change_theme)
        layout.addWidget(self.theme_box)
        return bar

    def _apply_query(self) -> None:
        self.board_view.set_query({
            "text": self.search_edit.text().strip(),
            "label_id": None,
            "priority": self.priority_filter.currentData(),
        })

    # ---- actions ----------------------------------------------------------
    def _open_board(self, board_id: str) -> None:
        self.controller.open_board(board_id)
        self._refresh_board()

    def _refresh_board(self) -> None:
        self.board_view.rebuild()
        self.sidebar.reload()

    def _edit_card(self, card_id: str) -> None:
        dialog = CardEditor(card_id, self.controller, self)
        if dialog.exec():
            self._refresh_board()

    def _manage_labels(self) -> None:
        LabelManager(self.controller, self).exec()
        self._refresh_board()

    def _change_theme(self, name: str) -> None:
        self.controller.set_theme(name)
        app = self.window().windowHandle()  # noqa: F841 (kept for clarity)
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(theme.qss(name))

    # ---- shortcuts --------------------------------------------------------
    def _install_shortcuts(self) -> None:
        focus_search = QAction(self)
        focus_search.setShortcut(QKeySequence("Ctrl+K"))
        focus_search.triggered.connect(lambda: self.search_edit.setFocus())
        self.addAction(focus_search)

        add_column = QAction(self)
        add_column.setShortcut(QKeySequence("Ctrl+Shift+N"))
        add_column.triggered.connect(self.board_view._add_column)
        self.addAction(add_column)


def controller_theme(controller: Controller) -> str:
    return controller.theme_name
```

- [ ] **Step 2: Export `MainWindow` from the ui package**

Replace `cachykanban/ui/__init__.py` with:

```python
"""CachyKanban Qt UI package."""

from .main_window import MainWindow

__all__ = ["MainWindow"]
```

- [ ] **Step 3: Sanity-check import (offscreen)**

Run:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from cachykanban.ui import MainWindow; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add cachykanban/ui/main_window.py cachykanban/ui/__init__.py
git commit -m "feat: add MainWindow wiring search, labels, theme, shortcuts"
```

---

## Task 19: App bootstrap + smoke test

**Files:**
- Create: `cachykanban/app.py`
- Create: `cachykanban/__main__.py`
- Test: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

`tests/test_smoke.py`:

```python
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"PySide6 unavailable: {exc}")
        cls.app = QApplication.instance() or QApplication([])

    def test_mainwindow_builds_against_temp_store(self):
        from cachykanban.controller import Controller
        from cachykanban.store import Store
        from cachykanban.ui import MainWindow

        with tempfile.TemporaryDirectory() as tmp:
            controller = Controller(Store(base=Path(tmp)))
            controller.load()
            controller.add_card(controller.board.columns[0].id, "smoke card")
            window = MainWindow(controller)
            window.show()
            # board view rebuilt without error and a default board is present
            self.assertEqual(window.windowTitle(), "CachyKanban")
            self.assertGreaterEqual(len(controller.board.columns), 1)
            window.close()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.test_smoke -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cachykanban.app'` (raised via `ui` import chain) or import error for `MainWindow` if app missing. (The test imports MainWindow, which is fine; the failure will be that `app.py`/`__main__.py` don't exist yet only matters in Step 4. If Step 2 unexpectedly passes, continue.)

- [ ] **Step 3: Create `cachykanban/app.py` and `cachykanban/__main__.py`**

`cachykanban/app.py`:

```python
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import __version__
from .controller import Controller
from .store import Store
from .ui import MainWindow
from .ui import theme


def main(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("CachyKanban")
    app.setApplicationDisplayName("CachyKanban")
    app.setApplicationVersion(__version__)

    controller = Controller(Store())
    controller.load()
    app.setStyleSheet(theme.qss(controller.theme_name))

    window = MainWindow(controller)
    window.show()
    return app.exec()
```

`cachykanban/__main__.py`:

```python
from .app import main


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run smoke test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.test_smoke -v`
Expected: PASS (1 test OK, or SKIPPED if no Qt platform — acceptable)

- [ ] **Step 5: Run the entire suite**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v`
Expected: PASS (all tests green)

- [ ] **Step 6: Commit**

```bash
git add cachykanban/app.py cachykanban/__main__.py tests/test_smoke.py
git commit -m "feat: add app bootstrap and headless smoke test"
```

---

## Task 20: Packaging — launcher, .desktop, icon, PKGBUILD

**Files:**
- Create: `data/cachykanban`
- Create: `data/io.github.tubbyhubby.CachyKanban.desktop`
- Create: `data/cachykanban.svg`
- Create: `packaging/arch/PKGBUILD`

- [ ] **Step 1: Create the launcher shim `data/cachykanban`**

```sh
#!/usr/bin/env sh
exec python -m cachykanban "$@"
```

- [ ] **Step 2: Create `data/io.github.tubbyhubby.CachyKanban.desktop`**

```ini
[Desktop Entry]
Type=Application
Name=CachyKanban
Comment=Offline Kanban board with customizable columns and cards
Exec=cachykanban
Icon=cachykanban
Terminal=false
Categories=Utility;Office;ProjectManagement;
Keywords=Kanban;Board;Tasks;Cards;Planning;
```

- [ ] **Step 3: Create the icon `data/cachykanban.svg`**

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="24" fill="#1b1d23"/>
  <rect x="22" y="28" width="24" height="72" rx="6" fill="#7c8596"/>
  <rect x="52" y="28" width="24" height="52" rx="6" fill="#6ea8fe"/>
  <rect x="82" y="28" width="24" height="38" rx="6" fill="#48bb78"/>
</svg>
```

- [ ] **Step 4: Create `packaging/arch/PKGBUILD`**

```bash
# Maintainer: tubbyhubby
pkgname=cachykanban
pkgver=0.1.0
pkgrel=1
pkgdesc="Offline Kanban board with customizable columns and cards (PySide6/Qt)"
arch=("any")
url="https://github.com/tubbyhubby/cachykanban"
license=("MIT")
depends=("python" "pyside6")

package() {
  cd "${startdir}/../.."
  local site_packages
  site_packages="$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
  install -dm755 "${pkgdir}${site_packages}"
  cp -a cachykanban "${pkgdir}${site_packages}/"
  find "${pkgdir}${site_packages}/cachykanban" -type d -name __pycache__ -prune -exec rm -rf {} +
  install -Dm755 data/cachykanban "${pkgdir}/usr/bin/cachykanban"
  install -Dm644 data/io.github.tubbyhubby.CachyKanban.desktop \
    "${pkgdir}/usr/share/applications/io.github.tubbyhubby.CachyKanban.desktop"
  install -Dm644 data/cachykanban.svg \
    "${pkgdir}/usr/share/icons/hicolor/scalable/apps/cachykanban.svg"
}
```

- [ ] **Step 5: Verify the launcher runs the module (offscreen, quick boot-and-quit)**

Run:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "import cachykanban.__main__; print('module entry importable')"
```
Expected: `module entry importable`

- [ ] **Step 6: Commit**

```bash
git add data/ packaging/
git commit -m "build: add Arch PKGBUILD, .desktop launcher, and icon"
```

---

## Task 21: README + manual verification

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# CachyKanban

Offline, native Kanban board for Arch Linux (PySide6/Qt). Multiple boards,
customizable columns, and cards with markdown notes, labels, checklists, and
priority. Local JSON storage — no account, no network.

## Run from source

```bash
python -m venv --system-site-packages .venv
.venv/bin/pip install -e .
.venv/bin/python -m cachykanban
```

## Tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
```

## Install (Arch)

```bash
cd packaging/arch
makepkg -si
```

## Data location

Boards are stored as JSON under `~/.local/share/cachykanban/`
(`index.json` + `boards/<id>.json`), with `.bak` copies for crash recovery.
```

- [ ] **Step 2: Full automated suite**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v`
Expected: PASS (all tests green)

- [ ] **Step 3: Manual verification (real window) — confirm each item**

Launch: `.venv/bin/python -m cachykanban`

Verify:
- [ ] App opens with a default "My Board" and three columns (Backlog / In Progress / Done).
- [ ] "+ New board" in the sidebar creates a board; clicking a board switches to it.
- [ ] Right-click a board → rename / change color / delete all work.
- [ ] "+ Add column" adds a column; the column menu (⋮) renames / recolors / deletes it.
- [ ] "+ Add card" adds a card; clicking a card opens the editor.
- [ ] In the editor: title, markdown notes (Preview tab renders), priority, label checkboxes, checklist add/remove/check, Archive, and Save all work.
- [ ] Drag a card within a column to reorder; drag a card to another column to move it.
- [ ] Drag a column header left/right to reorder columns.
- [ ] Type in search → cards filter live; priority filter narrows results; `Ctrl+K` focuses search.
- [ ] "Labels…" opens the manager; add/recolor/delete a label updates cards.
- [ ] Switch theme dropdown (dark/light) restyles the app.
- [ ] Quit and relaunch → all changes persisted.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with run/test/install instructions"
```

---

## Self-Review (completed during planning)

**Spec coverage** — every spec section maps to a task:
- Multiple boards → Tasks 9, 15
- Customizable columns (add/rename/recolor/reorder/delete) → Tasks 9, 13, 14
- Customizable cards (title/notes/labels/checklists/priority/archive) → Tasks 3, 9, 16
- Markdown notes → Task 16 (Qt `setMarkdown`)
- Drag-and-drop cards within/between columns → Tasks 12, 13
- Reorder columns by drag → Task 14
- Search/filter (text/label/priority) + Ctrl+K → Tasks 8, 18
- Atomic JSON storage + `.bak` recovery + schema version → Tasks 5, 6, 7
- Autosave on change → Task 9 (`_persist` after every mutation)
- Dark/light/system theme → Tasks 11, 18
- Error handling (corrupt board recovery, non-fatal) → Tasks 6, 7
- unittest suite (models/store/search/controller/theme/smoke) → Tasks 2–11, 19
- Arch packaging (PKGBUILD/.desktop/launcher/icon) → Task 20
- README → Task 21

**Deferred (per spec Non-Goals):** due dates, git-branch links, reminders, attachments, WIP limits, undo, calendar, sync — intentionally absent.

**Placeholder scan:** no TBD/TODO/"handle edge cases" steps; every code step contains complete code.

**Type consistency:** controller method names (`add_card`, `update_card`, `set_card_archived`, `move_card`, `add_column`, `rename_column`, `recolor_column`, `delete_column`, `reorder_columns`, `add_board`, `rename_board`, `recolor_board`, `delete_board`, `add_label`, `update_label`, `delete_label`, `open_board`, `set_theme`, `load`), store methods (`save_board`, `load_board`, `delete_board`, `board_exists`, `save_index`, `load_index`), models (`progress`, `find_column`, `find_card`, `find_label`, `summary`), search (`card_matches`, `priority_rank`, `visible_cards`), theme (`qss`, `palette`, `THEMES`), and mime constants (`CARD_MIME`, `COLUMN_MIME`) are referenced consistently across all tasks.

**Known v1 simplification:** the board-level label filter is exposed via the editor and Labels manager; the toolbar filters by text + priority (label filtering is available through `card_matches`/`visible_cards` and can be surfaced as a toolbar control in a later iteration). This is a deliberate scope trim, not a gap in the data/logic layer.
```
