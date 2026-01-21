#!/bin/bash
#
# Git commit and push script for Stock Market Words pipeline
# This runs after the pipeline completes to commit generated data
#

set -euo pipefail

# Configuration
REPO_DIR="/opt/stock-market-words"
COMMIT_MESSAGE="Auto-update: Daily pipeline run $(date +%Y-%m-%d)"

# Change to repository directory
cd "$REPO_DIR" || exit 1

# Check if we have any changes to commit
if git diff --quiet && git diff --cached --quiet; then
    echo "No changes to commit"
    exit 0
fi

# Configure git if not already done
if ! git config user.name > /dev/null 2>&1; then
    git config user.name "Stock Market Words Bot"
    git config user.email "bot@stockmarketwords.local"
fi

# Stage all changes in data and hugo directories
git add data/ hugo/site/static/data/ hugo/site/content/ 2>/dev/null || true

# Check if there are staged changes
if git diff --cached --quiet; then
    echo "No staged changes to commit"
    exit 0
fi

# Commit changes
git commit -m "$COMMIT_MESSAGE" || {
    echo "Commit failed"
    exit 1
}

# Push to remote (if configured)
# This will fail gracefully if no SSH key is set up or remote is not accessible
if git remote get-url origin > /dev/null 2>&1; then
    if git push origin main 2>&1; then
        echo "Successfully pushed changes to remote"
    else
        echo "WARNING: Failed to push changes - may need SSH key configuration"
        echo "Run: systemctl status stock-market-words.service for details"
        # Don't fail the service if push fails
        exit 0
    fi
else
    echo "No git remote configured - skipping push"
fi

exit 0
