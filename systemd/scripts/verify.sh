#!/bin/bash
#
# verify.sh — Non-destructive health checks for the Stock Market Words pipeline
#
# Validates that the systemd automation is correctly set up and ready to run.
# Safe to run at any time — makes no changes to the system.
#
# Usage:
#   sudo bash /opt/stock-market-words/systemd/scripts/verify.sh
#
# Exit codes:
#   0 = all checks pass
#   1 = one or more checks failed
#

set -uo pipefail

REPO_DIR="/opt/stock-market-words"
SERVICE_USER="smw"
VENV_DIR="$REPO_DIR/python3/venv"
DB_PATH="$REPO_DIR/data/market_data.db"
BOT_NAME="stockmarketwords-bot"

# ── Colors ───────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check_pass() { echo -e "  ${GREEN}✓${NC} $*"; ((PASS++)); }
check_fail() { echo -e "  ${RED}✗${NC} $*"; ((FAIL++)); }
check_warn() { echo -e "  ${YELLOW}!${NC} $*"; ((WARN++)); }

# ── 1. Service user ─────────────────────────────────────────────────
echo "── Service User ──"
if id "$SERVICE_USER" &>/dev/null; then
    check_pass "User '$SERVICE_USER' exists"
else
    check_fail "User '$SERVICE_USER' does not exist — run install.sh"
fi

# ── 2. Repository ───────────────────────────────────────────────────
echo "── Repository ──"
if [[ -d "$REPO_DIR/.git" ]]; then
    check_pass "Git repo at $REPO_DIR"
else
    check_fail "No git repo at $REPO_DIR"
fi

OWNER=$(stat -c '%U' "$REPO_DIR" 2>/dev/null || echo "unknown")
if [[ "$OWNER" == "$SERVICE_USER" ]]; then
    check_pass "Owned by $SERVICE_USER"
else
    check_fail "Owned by $OWNER (expected $SERVICE_USER)"
fi

# ── 3. Python venv ──────────────────────────────────────────────────
echo "── Python Environment ──"
if [[ -f "$VENV_DIR/bin/activate" ]]; then
    check_pass "Virtual environment exists"
else
    check_fail "No venv at $VENV_DIR"
fi

if [[ -f "$VENV_DIR/bin/ticker-cli" ]]; then
    check_pass "ticker-cli entry point installed"
else
    check_fail "ticker-cli not found in venv — run: pip install -e ."
fi

if sudo -u "$SERVICE_USER" bash -c "source '$VENV_DIR/bin/activate' && ticker-cli --help" &>/dev/null; then
    check_pass "ticker-cli --help succeeds as $SERVICE_USER"
else
    check_fail "ticker-cli --help fails as $SERVICE_USER"
fi

# ── 4. Database ──────────────────────────────────────────────────────
echo "── Database ──"
if [[ -f "$DB_PATH" ]]; then
    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    check_pass "Database exists ($DB_SIZE)"
else
    check_fail "No database at $DB_PATH — copy it or run ticker-cli init"
fi

if [[ -f "$DB_PATH" ]]; then
    # Check tables exist
    TABLES=$(sudo -u "$SERVICE_USER" sqlite3 "$DB_PATH" ".tables" 2>/dev/null || echo "")
    if echo "$TABLES" | grep -q "tickers"; then
        check_pass "Table 'tickers' present"
    else
        check_fail "Table 'tickers' missing — run ticker-cli init"
    fi
    if echo "$TABLES" | grep -q "daily_metrics"; then
        check_pass "Table 'daily_metrics' present"
    else
        check_fail "Table 'daily_metrics' missing"
    fi

    # Check for recent data
    TICKER_COUNT=$(sudo -u "$SERVICE_USER" sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM tickers WHERE is_active=1;" 2>/dev/null || echo "0")
    if [[ "$TICKER_COUNT" -gt 0 ]]; then
        check_pass "Active tickers: $TICKER_COUNT"
    else
        check_warn "No active tickers in database (expected if fresh install)"
    fi
fi

# ── 5. Git identity ─────────────────────────────────────────────────
echo "── Git Identity ──"
GIT_SCRIPT="$REPO_DIR/systemd/scripts/git-commit-and-push.sh"
if [[ -f "$GIT_SCRIPT" ]]; then
    if grep -q "$BOT_NAME" "$GIT_SCRIPT"; then
        check_pass "Git script uses bot identity '$BOT_NAME'"
    else
        check_fail "Git script does not reference '$BOT_NAME'"
    fi
    if [[ -x "$GIT_SCRIPT" ]]; then
        check_pass "Git script is executable"
    else
        check_fail "Git script is not executable — chmod +x $GIT_SCRIPT"
    fi
else
    check_fail "Git script not found at $GIT_SCRIPT"
fi

# ── 6. SSH key ───────────────────────────────────────────────────────
echo "── SSH / Push ──"
SMW_HOME=$(eval echo "~$SERVICE_USER" 2>/dev/null || echo "$REPO_DIR")
if [[ -f "$SMW_HOME/.ssh/id_ed25519" ]] || [[ -f "$SMW_HOME/.ssh/id_rsa" ]]; then
    check_pass "SSH key found for $SERVICE_USER"
else
    check_warn "No SSH key for $SERVICE_USER — git push will fail"
fi

if sudo -u "$SERVICE_USER" ssh -T git@github.com 2>&1 | grep -qi "successfully authenticated"; then
    check_pass "SSH auth to GitHub works"
else
    check_warn "SSH auth to GitHub failed — push may not work"
fi

# ── 7. Systemd timer ────────────────────────────────────────────────
echo "── Systemd Timers ──"
if systemctl is-enabled stock-market-words.timer &>/dev/null; then
    check_pass "Pipeline timer is enabled"
else
    check_fail "Pipeline timer is not enabled — run: systemctl enable stock-market-words.timer"
fi

if systemctl is-active stock-market-words.timer &>/dev/null; then
    check_pass "Pipeline timer is active"
else
    check_fail "Pipeline timer is not active — run: systemctl start stock-market-words.timer"
fi

NEXT_FIRE=$(systemctl show stock-market-words.timer -p NextElapseUSecRealtime --value 2>/dev/null || echo "")
if [[ -n "$NEXT_FIRE" && "$NEXT_FIRE" != "n/a" ]]; then
    check_pass "Pipeline next fire: $NEXT_FIRE"
else
    check_warn "Could not determine pipeline next fire time"
fi

if systemctl is-enabled pia-rotate.timer &>/dev/null; then
    check_pass "PIA rotation timer is enabled"
else
    check_warn "PIA rotation timer is not enabled (optional — run: systemctl enable pia-rotate.timer)"
fi

# ── 8. PIA VPN ──────────────────────────────────────────────────────
echo "── PIA VPN (Optional) ──"
if command -v piactl &>/dev/null; then
    check_pass "piactl is installed"
    PIA_STATE=$(piactl get connectionstate 2>/dev/null || echo "Unknown")
    if [[ "$PIA_STATE" == *"Connected"* ]]; then
        PIA_IP=$(piactl get vpnip 2>/dev/null || echo "unknown")
        check_pass "VPN connected (IP: $PIA_IP)"
    else
        check_warn "VPN not connected (state: $PIA_STATE) — rotation will be skipped"
    fi
else
    check_warn "piactl not installed — VPN rotation disabled (pipeline still works via backoff)"
fi

# ── 9. ticker-cli status ────────────────────────────────────────────
echo "── Pipeline Status ──"
STATUS_OUTPUT=$(sudo -u "$SERVICE_USER" bash -c "cd '$REPO_DIR/python3' && source venv/bin/activate && ticker-cli status" 2>&1) || true
if echo "$STATUS_OUTPUT" | grep -qi "error\|traceback"; then
    check_fail "ticker-cli status reported errors"
    echo "    $STATUS_OUTPUT" | head -5
else
    check_pass "ticker-cli status OK"
fi

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo -e " Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, ${YELLOW}$WARN warnings${NC}"
echo "═══════════════════════════════════════════════════════════"

if [[ $FAIL -gt 0 ]]; then
    exit 1
else
    exit 0
fi
