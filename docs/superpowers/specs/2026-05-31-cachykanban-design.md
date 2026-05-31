# CachyKanban — Design Spec

**Date:** 2026-05-31
**Status:** Approved (pending spec review)
**Author:** tubbyhubby (with Claude Code)

## Summary

CachyKanban is a fast, offline, single-user **native desktop Kanban app** for Arch
Linux, built with Python + PySide6/Qt. It manages multiple boards (one per project),
each with fully customizable columns ("categories") and richly customizable cards.
It is the user's replacement for Kangentic (dropped for being too slow) as the
personal planning/tracking front door, while the Codex coordinator / git-worktree
flow remains the execution layer.

Inspiration: [Brisqi](https://brisqi.com/) — an offline-first personal Kanban.
CachyKanban deliberately stays **native** (no Electron/browser) for speed and a
true desktop feel.

## Goals

- Native, offline, single-user desktop app — no network, no account, no Electron.
- Multiple boards in a left sidebar, switchable instantly.
- Customizable **categories** = columns: add / rename / recolor / reorder / delete.
- Customizable **cards**: title, markdown notes, colored labels, checklists, priority.
- Drag-and-drop cards within and between columns; reorder columns.
- Fast search/filter across a board.
- Durable local storage that never loses data on a crash.
- Ships as an Arch package with a desktop launcher.

## Non-Goals (explicitly deferred, not in v1)

Due dates · git-branch/worktree links · reminders/notifications · attachments ·
per-repo versioned boards · WIP limits · undo history · calendar view · any sync or
multi-device. These were considered and consciously cut from v1 to keep scope tight.

## Tech Stack

- **Language:** Python (>=3.10)
- **UI:** PySide6 / Qt Widgets
- **Persistence:** plain JSON files (human-readable, git-friendly)
- **Tests:** `unittest.TestCase`, run via `pytest` (dev dependency) or
  `python -m unittest`
- **Packaging:** `pyproject.toml` (setuptools) + Arch `PKGBUILD` + `.desktop` entry

This mirrors the structure and conventions of the existing `godot-plugin-updater`
app (same author, same machine): setuptools build, `[project.gui-scripts]` entry
point, `unittest`-style tests, an Arch `PKGBUILD` that builds a wheel and installs a
`.desktop` file + icon.

## Architecture

**Core principle — isolate pure logic from Qt.** `models.py`, `store.py`, and
`search.py` have **zero Qt dependency** and are fully unit-testable without a
display. Qt widgets under `ui/` are thin views. `controller.py` is the single place
that wires model mutations to persistence and view refreshes. This keeps each file
focused and the business logic testable in isolation.

### Project layout

```
~/Projects/cachykanban/
  pyproject.toml              # entry point: cachykanban = cachykanban.app:main
  README.md
  .gitignore
  cachykanban/
    __init__.py               # __version__
    app.py                    # QApplication bootstrap, theme, open MainWindow
    models.py                 # PURE dataclasses: Board, Column, Card, Label,
                              #   ChecklistItem (+ to_dict/from_dict). No Qt.
    store.py                  # persistence: load/save JSON, atomic writes, XDG
                              #   paths, schema version, .bak recovery. No Qt.
    search.py                 # PURE filter/sort over models (text/label/priority)
    controller.py             # mediates model mutations -> persistence -> refresh
    ui/
      __init__.py             # re-exports MainWindow
      main_window.py          # sidebar + board area + toolbar/search
      sidebar.py              # board list: add/rename/recolor/reorder/delete
      board_view.py           # columns area; drag cards; reorder columns
      column_widget.py        # one column: header (name/color/count) + card list
      card_widget.py          # compact card face: labels, title, meta row
      card_editor.py          # modal dialog: edit all card fields + archive
      label_manager.py        # per-board label palette (name + color)
      theme.py                # QSS: dark (default) / light / follow-system
  tests/
    __init__.py
    test_models.py            # serialization round-trips + invariants
    test_store.py             # save/load, atomic write, corrupt-file recovery
    test_search.py            # filter/sort logic
    test_smoke.py             # construct MainWindow against a temp store
  data/
    io.github.tubbyhubby.CachyKanban.desktop
    cachykanban.svg           # app icon
  packaging/
    arch/PKGBUILD             # pkgname=cachykanban; depends python-pyside6
```

### Unit responsibilities

- **models.py** — Data only. Each dataclass owns `to_dict()` / `from_dict()`.
  Depends on: nothing (stdlib `dataclasses`).
- **store.py** — Reads/writes board JSON to the XDG data dir, atomically; recovers
  from corruption via `.bak`. Depends on: `models`, stdlib.
- **search.py** — Given a board + query (text, label, priority), returns the
  filtered/sorted cards. Depends on: `models`.
- **controller.py** — The mutation API the UI calls (add card, move card, rename
  column, …). Applies the change to the in-memory model, asks `store` to persist
  (debounced), and signals the view to refresh. Depends on: `models`, `store`,
  `search`.
- **ui/** — Thin Qt views. Render model state; emit user intents to the controller.
  Depends on: `controller`, `models`, PySide6.

## Data Model

```
Board:    id, name, color, columns[], labels[], created, updated
Column:   id, name, color, cards[]               # the customizable "category"
Card:     id, title, notes(markdown), label_ids[], checklist[],
          priority(none|low|med|high), archived, created, updated
Label:    id, name, color                        # board-scoped palette
ChecklistItem: text, done
```

- IDs: short unique strings (e.g. `uuid4().hex[:8]`).
- All dataclasses serialize via `to_dict()` / reconstruct via `from_dict()`.
- `priority` is an enum-like string with a fixed set; `none` renders no marker.

## Storage

- **Location:** `~/.local/share/cachykanban/` (honors `$XDG_DATA_HOME`).
- **Files:** `index.json` (board order + lightweight metadata) and
  `boards/<board_id>.json` (one file per board, full content).
- **Atomic writes:** write to a temp file in the same dir, `os.replace()` into
  place — never a partial file.
- **Backup:** before overwriting, keep the previous good copy as `<file>.bak`.
- **Autosave:** debounced save on every change, plus a flush on window close.
- **Schema:** each file carries a `version` integer for future migrations.
- The data dir is plain JSON, so the user can `git init` it independently for
  versioned backups if desired (not done by the app).

## UI / Interaction

- **Sidebar (left):** list of boards; `+` adds a board; right-click → rename /
  recolor / delete; drag to reorder. Selecting a board loads it in the main area.
- **Board area (center):** columns laid out horizontally with horizontal scroll.
  Drag cards within a column to reorder and between columns to recategorize. Drag
  column headers to reorder columns. `+ Add column` at the right end;
  `+ Add card` at the bottom of each column.
- **Card editor:** clicking a card opens a modal dialog with title, markdown notes
  (edit + rendered preview), label picker, checklist editor, priority selector, and
  an Archive action.
- **Search / filter bar (top):** filter the current board by text, label, and/or
  priority. `Ctrl+K` focuses the search field.
- **Keyboard shortcuts:** for the common actions (new card, new column, search,
  switch board) — power-user friendly, matching the user's terminal-first habits.

## Theme

QSS-based theming with one accent color. **Dark by default**, plus **light** and
**follow-system** options. Quiet, clean, Brisqi-like — content first, chrome
minimal.

## Error Handling & Data Safety

- Atomic writes + `.bak` make a crash-safe save path.
- On load, validate each board file. If one is corrupt, move it aside (keep the
  `.bak`), surface a **non-blocking** message, and continue loading the rest rather
  than crashing the app.
- A missing data dir is created on first run with an empty default board.
- The `version` field allows painless schema migration later.

## Testing

Tests use `unittest.TestCase` (run via `pytest` or `python -m unittest`), matching
the sibling project:

- **test_models.py** — round-trip serialization for every dataclass; invariants
  (e.g. moving a card preserves it; IDs stay unique).
- **test_store.py** — save then load returns equal data; atomic write leaves no
  partial file; a deliberately corrupted board file triggers `.bak` recovery and a
  reported (not fatal) error.
- **test_search.py** — text/label/priority filters and sort order.
- **test_smoke.py** — construct `MainWindow` against a temp data dir (using
  `QApplication` offscreen) to catch import/wiring breakage. Skips cleanly if no Qt
  platform is available.

## Packaging (Arch)

- `pyproject.toml` with a `[project.gui-scripts]` entry:
  `cachykanban = cachykanban.app:main`.
- `packaging/arch/PKGBUILD`: `pkgname=cachykanban`, `arch=('any')`,
  `depends=('python' 'python-pyside6')`, builds a wheel with `python -m build` and
  installs it with `python -m installer`, then installs the `.desktop` file and the
  `cachykanban.svg` icon — same shape as `godot-plugin-updater`.
- `data/io.github.tubbyhubby.CachyKanban.desktop`: `Categories=Utility;Office;`,
  `Exec=cachykanban`, `Icon=cachykanban`.

## v1 Scope Checklist

In v1: multiple boards · columns (add/rename/recolor/reorder/delete) · cards
(title, markdown notes, labels, checklists, priority) · drag-and-drop · search/
filter · archive · dark/light/system theme · autosave with atomic writes + backup ·
Arch package · unittest suite.

Deferred: see **Non-Goals** above.

## Open Decisions (resolved)

- **Name:** CachyKanban (fits CachyOS).
- **Storage:** central `~/.local/share/cachykanban/`, JSON-per-board (chosen over
  SQLite for transparency and git-friendliness).
- **Card editor:** modal dialog (chosen over docked side-panel for v1 simplicity).
- **Theme default:** dark, with follow-system available.
- **Card features in v1:** checklists + priority (due dates and git-branch links
  deferred).
