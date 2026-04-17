#!/bin/bash
#
# Git commit and push script for Stock Market Words pipeline
# Commits daily pipeline output as stockmarketwords-bot
#
# Called via ExecStartPost in stock-market-words.service
#

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────
REPO_DIR="/opt/stock-market-words"
BOT_NAME="stockmarketwords-bot"
BOT_EMAIL="stockmarketwords-bot@users.noreply.github.com"
TODAY=$(date +%Y-%m-%d)
HOSTNAME=$(hostname)

# ── Change to repo ──────────────────────────────────────────────────
cd "$REPO_DIR" || exit 1

# ── Check for changes ───────────────────────────────────────────────
if git diff --quiet && git diff --cached --quiet; then
    echo "[bot] No changes to commit for $TODAY"
    exit 0
fi

# ── Stage pipeline output ───────────────────────────────────────────
git add \
    data/ \
    hugo/site/static/data/ \
    hugo/site/data/ \
    hugo/site/content/ \
    2>/dev/null || true

# Bail if nothing was staged
if git diff --cached --quiet; then
    echo "[bot] No staged changes to commit for $TODAY"
    exit 0
fi

# ── Count what changed ──────────────────────────────────────────────
CHANGED_FILES=$(git diff --cached --numstat | wc -l)

# ── Commit with bot identity ────────────────────────────────────────
export GIT_AUTHOR_NAME="$BOT_NAME"
export GIT_AUTHOR_EMAIL="$BOT_EMAIL"
export GIT_COMMITTER_NAME="$BOT_NAME"
export GIT_COMMITTER_EMAIL="$BOT_EMAIL"

git commit -m "Daily data update: $TODAY" -m "Pipeline: ticker-cli run-all
Host: $HOSTNAME
Files changed: $CHANGED_FILES" || {
    echo "[bot] ERROR: commit failed"
    exit 1
}

echo "[bot] Committed as $BOT_NAME <$BOT_EMAIL>"

# ── Push to remote ──────────────────────────────────────────────────
if git remote get-url origin > /dev/null 2>&1; then
    if git push origin main 2>&1; then
        echo "[bot] Pushed to origin/main"
    else
        echo "[bot] WARNING: push failed (SSH key or network issue)"
        # Don't fail the service — data is committed locally
        exit 0
    fi
else
    echo "[bot] No git remote configured — skipping push"
fi

exit 0
