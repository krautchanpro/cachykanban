#!/usr/bin/env bash
# Install a user-level desktop entry so CachyKanban appears in the application
# menu (KDE/GNOME) and can be pinned or double-clicked like any installed app.
# No root required; installs under ~/.local. Re-run any time to refresh paths.
set -euo pipefail

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
ROOT="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

LAUNCHER="$ROOT/run-cachykanban.sh"
chmod +x "$LAUNCHER"

APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
DESKTOP_FILE="$APPS_DIR/io.github.tubbyhubby.CachyKanban.desktop"

mkdir -p "$APPS_DIR" "$ICONS_DIR"
install -m644 "$ROOT/data/cachykanban.svg" "$ICONS_DIR/cachykanban.svg"

# Also install sized PNGs when a rasterizer is available — some panels and
# launchers prefer fixed-size PNGs over the scalable SVG.
ICON_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
if command -v rsvg-convert >/dev/null 2>&1; then
    for s in 16 32 48 64 128 256; do
        mkdir -p "$ICON_ROOT/${s}x${s}/apps"
        rsvg-convert -w "$s" -h "$s" "$ROOT/data/cachykanban.svg" \
            -o "$ICON_ROOT/${s}x${s}/apps/cachykanban.png" 2>/dev/null || true
    done
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=CachyKanban
Comment=Offline Kanban board with customizable columns and cards
Exec=$LAUNCHER
Icon=cachykanban
Terminal=false
Categories=Office;ProjectManagement;
Keywords=Kanban;Board;Tasks;Cards;Planning;
EOF
chmod +x "$DESKTOP_FILE"

# Refresh the menu/icon caches if the tools are available (best-effort).
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -q "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" 2>/dev/null || true

echo "Installed: $DESKTOP_FILE"
echo "Icon:      $ICONS_DIR/cachykanban.svg"
echo "CachyKanban should now appear in your application launcher."
