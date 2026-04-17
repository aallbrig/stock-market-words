#!/bin/bash
#
# install.sh — Set up Stock Market Words pipeline on an Ubuntu host
#
# Prerequisites:
#   - Ubuntu 20.04+ with systemd
#   - Repo already cloned to /opt/stock-market-words
#   - Run as root (or with sudo)
#
# Usage:
#   sudo bash /opt/stock-market-words/systemd/scripts/install.sh
#

set -euo pipefail

REPO_DIR="/opt/stock-market-words"
SERVICE_USER="smw"
VENV_DIR="$REPO_DIR/python3/venv"

# ── Colors ───────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
fail()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── Pre-flight ───────────────────────────────────────────────────────
[[ $EUID -eq 0 ]] || fail "Must run as root (use sudo)"
[[ -d "$REPO_DIR" ]] || fail "Repo not found at $REPO_DIR — clone it first"
command -v python3 >/dev/null || fail "python3 not found — install it first"
command -v git >/dev/null || fail "git not found — install it first"

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Python $PYTHON_VERSION detected"

# ── Step 1: Create service user ─────────────────────────────────────
if id "$SERVICE_USER" &>/dev/null; then
    info "User '$SERVICE_USER' already exists"
else
    useradd -r -s /bin/bash -d "$REPO_DIR" -M "$SERVICE_USER"
    info "Created system user '$SERVICE_USER'"
fi

# ── Step 2: Fix ownership ───────────────────────────────────────────
chown -R "$SERVICE_USER:$SERVICE_USER" "$REPO_DIR"
info "Ownership set to $SERVICE_USER:$SERVICE_USER"

# ── Step 3: Create Python venv and install deps ─────────────────────
if [[ -f "$VENV_DIR/bin/ticker-cli" ]]; then
    info "Virtual environment and ticker-cli already installed"
else
    echo "Setting up Python virtual environment..."
    sudo -u "$SERVICE_USER" bash -c "
        cd '$REPO_DIR/python3'
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip --quiet
        pip install -e . --quiet
    "
    info "Virtual environment created, ticker-cli installed"
fi

# ── Step 4: Initialize database (if no existing DB) ─────────────────
DB_PATH="$REPO_DIR/data/market_data.db"
if [[ -f "$DB_PATH" ]]; then
    info "Database exists at $DB_PATH ($(du -h "$DB_PATH" | cut -f1))"
else
    warn "No database found — initializing empty database"
    sudo -u "$SERVICE_USER" bash -c "
        cd '$REPO_DIR/python3'
        source venv/bin/activate
        ticker-cli init
    "
    info "Database initialized"
fi

# ── Step 5: Make scripts executable ─────────────────────────────────
chmod +x "$REPO_DIR/systemd/scripts/"*.sh
info "Scripts marked executable"

# ── Step 6: Install systemd units ───────────────────────────────────
cp "$REPO_DIR/systemd/system/stock-market-words.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/system/stock-market-words.timer" /etc/systemd/system/
systemctl daemon-reload
info "Systemd units installed and daemon reloaded"

# ── Step 7: Enable and start timer ──────────────────────────────────
systemctl enable --now stock-market-words.timer
info "Timer enabled and started"

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo " Installation complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo " Next steps:"
echo "   1. Copy your database:  scp data/market_data.db $SERVICE_USER@$(hostname):$DB_PATH"
echo "   2. Set up SSH key:      sudo su - $SERVICE_USER -c 'ssh-keygen -t ed25519'"
echo "   3. Add deploy key to GitHub repo (with write access)"
echo "   4. Configure git remote: sudo su - $SERVICE_USER -c 'cd $REPO_DIR && git remote set-url origin git@github.com:aallbrig/stock-market-words.git'"
echo "   5. Run verify:          sudo bash $REPO_DIR/systemd/scripts/verify.sh"
echo "   6. Test manually:       sudo systemctl start stock-market-words.service"
echo ""
echo " Timer status:"
systemctl list-timers stock-market-words.timer --no-pager
echo ""
