#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_path="$project_root/.venv/bin/python"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
unit_path="$unit_dir/cachykanban-web.service"

if [[ ! -x "$python_path" ]]; then
  echo "CachyKanban's virtual environment is missing; run ./run-cachykanban.sh once first." >&2
  exit 1
fi

mkdir -p "$unit_dir"
sed \
  -e "s|@PROJECT_ROOT@|$project_root|g" \
  -e "s|@PYTHON@|$python_path|g" \
  "$project_root/systemd/cachykanban-web.service.in" > "$unit_path"

systemctl --user daemon-reload
systemctl --user enable --now cachykanban-web.service
tailscale serve --bg --https=8444 http://127.0.0.1:8766

dns_name="$(tailscale status --json | "$python_path" -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
echo "CachyKanban is available at https://$dns_name:8444"
