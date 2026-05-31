#!/usr/bin/env bash
# Double-clickable launcher for CachyKanban.
# Finds (or creates) the project venv, then runs the app. Works from anywhere.
set -euo pipefail

# Resolve the real directory of this script, following symlinks.
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
ROOT="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"
PY="$VENV/bin/python"

notify() {
    command -v notify-send >/dev/null 2>&1 && notify-send "CachyKanban" "$1" || true
}

die() {
    notify "$1"
    # Also surface the error if launched from a terminal.
    echo "CachyKanban: $1" >&2
    exit 1
}

# Bootstrap the venv on first run.
if [ ! -x "$PY" ]; then
    command -v python >/dev/null 2>&1 || die "python not found on PATH"
    notify "First run: setting up… this can take a moment."
    python -m venv --system-site-packages "$VENV" || die "could not create venv"
    "$PY" -m pip install -e "$ROOT" >/dev/null 2>&1 || die "could not install dependencies"
fi

exec "$PY" -m cachykanban "$@"
