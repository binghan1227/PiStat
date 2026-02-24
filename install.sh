#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_USER="$(whoami)"
PYTHON="$DIR/.venv/bin/python3"
SERVICE_NAME="pistat"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ "${1:-}" == "--uninstall" ]]; then
    sudo systemctl stop "$SERVICE_NAME" || true
    sudo systemctl disable "$SERVICE_NAME" || true
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
    echo "PiStat uninstalled."
    exit 0
fi

# Fall back to system python3 if venv doesn't exist
if [[ ! -x "$PYTHON" ]]; then
    PYTHON="$(command -v python3)"
fi

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=PiStat System Monitor Dashboard
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${DIR}
ExecStart=${PYTHON} ${DIR}/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

PORT="$(grep -E '^\s*port\s*=' "$DIR/config.toml" | head -1 | awk -F'=' '{print $2}' | tr -d ' ')"
PORT="${PORT:-8889}"
echo "PiStat installed and started. Open http://$(hostname -I | awk '{print $1}'):${PORT}"
