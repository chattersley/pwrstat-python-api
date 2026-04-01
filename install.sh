#!/usr/bin/env bash
# Installs pwrstat-api as a systemd service on a Debian system.
# Run as root: sudo bash install.sh

set -euo pipefail

INSTALL_DIR="/opt/pwrstat-api"
SERVICE_USER="pwrstat-api"
SERVICE_FILE="pwrstat-api.service"

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (sudo bash install.sh)" >&2
    exit 1
fi

# ── Install uv if not present ────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Make uv available in current shell
    export PATH="$HOME/.local/bin:$PATH"
fi

# ── Create dedicated service user ────────────────────────────────────────────
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Creating user $SERVICE_USER..."
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# ── Copy project to install directory ────────────────────────────────────────
echo "Installing to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
rsync -a --exclude='.git' --exclude='.venv' "$(dirname "$0")/" "$INSTALL_DIR/"

# ── Create virtual environment and install dependencies ──────────────────────
cd "$INSTALL_DIR"
uv sync --no-dev
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# ── Install systemd service ───────────────────────────────────────────────────
echo "Installing systemd service..."
cp "$INSTALL_DIR/$SERVICE_FILE" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_FILE"
systemctl restart "$SERVICE_FILE"

echo ""
echo "Done. Service status:"
systemctl status pwrstat-api --no-pager
