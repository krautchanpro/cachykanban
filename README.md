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

The `--system-site-packages` flag lets the venv use the system `pyside6` package
(install it with `sudo pacman -S pyside6` if needed) instead of building PySide6.

## Tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
```

The pure-logic layers (models, store, search, controller) and the theme are
fully unit-tested; a headless smoke test builds the main window against a
temporary data directory.

## Install (Arch)

```bash
cd packaging/arch
makepkg -si
```

## Data location

Boards are stored as JSON under `~/.local/share/cachykanban/`
(`index.json` + `boards/<id>.json`), with `.bak` copies for crash recovery.
Honors `$XDG_DATA_HOME`.

## Features

- Multiple boards in a left sidebar (add / rename / recolor / delete)
- Customizable columns: add, rename, recolor, drag-reorder, delete
- Cards with title, markdown notes (live preview), colored labels, checklists,
  and priority
- Drag-and-drop cards within and between columns
- Live search plus priority filter; `Ctrl+K` focuses search
- Per-board label palette manager
- Dark / light / follow-system theme
- Atomic autosave with `.bak` corruption recovery
