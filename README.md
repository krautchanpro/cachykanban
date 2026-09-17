# CachyKanban

Offline, native Kanban board for Arch Linux (PySide6/Qt). Multiple projects,
each with multiple boards, customizable columns, and cards with markdown notes,
labels, checklists, and priority. Local JSON storage with an optional private
web interface for access from other devices on the same Tailscale network.

## Private remote access

The companion web interface uses the same project files as the desktop app. It
supports switching projects and boards, adding and editing cards, labels,
checklists, priorities, moving cards between columns, archiving, and deletion.
It listens only on `127.0.0.1:8766`; Tailscale Serve supplies private HTTPS to
devices signed into this tailnet.

Install and start it once:

```bash
./install-web.sh
```

Then open:

`https://your-device.your-tailnet.ts.net:8444`

The installer prints the exact private URL for the current Tailscale network.

Operations:

```bash
systemctl --user status cachykanban-web
systemctl --user restart cachykanban-web
journalctl --user -u cachykanban-web -f
tailscale serve status
```

To stop remote access without deleting any board data:

```bash
tailscale serve --https=8444 off
systemctl --user disable --now cachykanban-web
```

Do not expose this service with Tailscale Funnel or router port forwarding. The
web interface is intended only for the private tailnet. An open desktop app
automatically detects remote card changes and refreshes within about two
seconds, while keeping its current project and board selected. Project, board,
column, and label management remain in the desktop app; the remote interface is
focused on cards.

## Double-click to run

Two no-terminal options:

- **Add it to your application menu (recommended):** run `./install-desktop.sh`
  once. "CachyKanban" then appears in your KDE/GNOME launcher with its icon, and
  can be pinned to the taskbar. The installer is user-level (no root, installs
  under `~/.local`); re-run it if you move the project folder.
- **Double-click the launcher in the file manager:** double-click
  `run-cachykanban.sh` and choose *Execute*. It creates the virtualenv on first
  run, then starts the app. (In Dolphin you may need to mark it executable once:
  right-click → Properties → Permissions → "Is executable".)

## Run from source

```bash
python -m venv --system-site-packages .venv
.venv/bin/pip install -e .
.venv/bin/python -m cachykanban
```

The `--system-site-packages` flag lets the venv use the system `pyside6` package
(install it with `sudo pacman -S pyside6` if needed) instead of building PySide6.
The `run-cachykanban.sh` launcher automates exactly these steps.

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

Projects are stored as one self-contained JSON file per project under
`~/.local/share/cachykanban/projects/` (`<project-id>.json`). Each file nests
that project's boards, columns, labels, and cards; `.bak` copies are written
for crash recovery. `index.json` contains only project summaries, the active
project ID, and app settings. Honors `$XDG_DATA_HOME`.

On first launch after upgrading from v1, the old `boards/<id>.json` files are
wrapped into one project each. Those legacy files are intentionally left in
place as recovery copies; migration is safe to retry and skips stale or
corrupt index entries.

## Features

- Multiple projects and boards selected from distinct top-left dropdowns (add /
  rename / recolor / delete from their adjacent menus)
- Customizable columns: add, rename, recolor, drag-reorder, delete
- Cards with title, markdown notes (live preview), colored labels, checklists,
  and priority
- Drag-and-drop cards within and between columns
- Live search plus priority filter; `Ctrl+K` focuses search
- Per-board label palette manager
- Dark / light / follow-system theme
- Atomic autosave with `.bak` corruption recovery
