#!/bin/bash
#
# backup-db-s3.sh — Back up SQLite database to AWS S3 after pipeline run
#
# Called via ExecStartPost in stock-market-words.service (optional).
# Requires: sqlite3, aws cli, and AWS credentials in ~smw/.aws/
#
# Usage:
#   sudo -u smw /opt/stock-market-words/systemd/scripts/backup-db-s3.sh
#

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────
REPO_DIR="/opt/stock-market-words"
DB_PATH="$REPO_DIR/data/market_data.db"
S3_BUCKET="smw-database-backups"
S3_PREFIX="daily-backups"
AWS_PROFILE="smw-backup"
TODAY=$(date +%Y-%m-%d)
S3_KEY="${S3_PREFIX}/market_data_${TODAY}.db"
HOSTNAME=$(hostname)

log() { echo "[backup] $(date '+%H:%M:%S') $*"; }

# ── Pre-flight ───────────────────────────────────────────────────────
if [[ ! -f "$DB_PATH" ]]; then
    log "ERROR: Database not found at $DB_PATH"
    exit 1
fi

if ! command -v aws &>/dev/null; then
    log "WARNING: aws CLI not installed — skipping S3 backup"
    exit 0
fi

if ! aws sts get-caller-identity --profile "$AWS_PROFILE" &>/dev/null; then
    log "WARNING: AWS credentials not configured — skipping S3 backup"
    exit 0
fi

DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
log "Starting backup: $DB_PATH ($DB_SIZE) → s3://$S3_BUCKET/$S3_KEY"

# ── Create consistent snapshot ───────────────────────────────────────
TEMP_BACKUP=$(mktemp /tmp/market_data_backup_XXXXXX.db)
trap 'rm -f "$TEMP_BACKUP"' EXIT

sqlite3 "$DB_PATH" ".backup $TEMP_BACKUP" 2>&1 || {
    log "ERROR: sqlite3 .backup failed"
    exit 1
}

# ── Verify integrity ────────────────────────────────────────────────
INTEGRITY=$(sqlite3 "$TEMP_BACKUP" "PRAGMA integrity_check;" 2>&1)
if [[ "$INTEGRITY" != "ok" ]]; then
    log "ERROR: Backup integrity check failed: $INTEGRITY"
    exit 1
fi
log "Integrity check passed"

# ── Upload to S3 ────────────────────────────────────────────────────
aws s3 cp "$TEMP_BACKUP" "s3://${S3_BUCKET}/${S3_KEY}" \
    --profile "$AWS_PROFILE" \
    --sse AES256 \
    --storage-class ONEZONE_IA \
    --metadata "backup-date=${TODAY},hostname=${HOSTNAME}" \
    --quiet 2>&1 || {
    log "ERROR: S3 upload failed"
    exit 1
}

log "Uploaded to s3://$S3_BUCKET/$S3_KEY"

# ── Verify upload ────────────────────────────────────────────────────
if aws s3 ls "s3://${S3_BUCKET}/${S3_KEY}" --profile "$AWS_PROFILE" &>/dev/null; then
    log "Upload verified"
else
    log "WARNING: Upload verification failed (object not found)"
    exit 1
fi

log "Backup complete"
exit 0
