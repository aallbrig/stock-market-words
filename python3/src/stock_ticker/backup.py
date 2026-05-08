"""
SQLite database backup, restore, and retention utilities.

Backup types
------------
- daily     : one per day, created by the nightly systemd timer (or manually).
              Pruned after STOCK_TICKER_BACKUP_RETENTION_DAYS (default 14).
- prerestore: created automatically before every restore operation.
              Pruned on the same schedule as the daily backup for that date
              (i.e. when date + retention_days < today).

File format: market_data_YYYYMMDD_HHMMSS[_prerestore].sql.gz
             ~16 MB gzipped vs ~95 MB uncompressed (5-6x ratio).

Configuration
-------------
STOCK_TICKER_BACKUP_DIR            override backup directory
STOCK_TICKER_BACKUP_RETENTION_DAYS override retention window (default 14)
"""

import gzip
import os
import re
import sqlite3
from datetime import date, timedelta, timezone, datetime
from pathlib import Path


BACKUP_TYPE_DAILY = "daily"
BACKUP_TYPE_PRERESTORE = "prerestore"

_FILENAME_RE = re.compile(
    r"^market_data_(\d{8})_\d{6}(_prerestore)?\.sql\.gz$"
)
_LEGACY_FILENAME_RE = re.compile(
    r"^market_data_(\d{8})_\d{6}\.sql$"
)

_DEFAULT_RETENTION_DAYS = 14


def get_backup_dir() -> Path:
    env = os.environ.get("STOCK_TICKER_BACKUP_DIR")
    if env:
        d = Path(env)
    else:
        # Resolve relative to the project root (two levels above this file's package)
        d = Path(__file__).parent.parent.parent.parent / "data" / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _retention_days() -> int:
    return int(os.environ.get("STOCK_TICKER_BACKUP_RETENTION_DAYS", _DEFAULT_RETENTION_DAYS))


def create_backup(db_path="data/market_data.db", backup_type=BACKUP_TYPE_DAILY) -> str:
    """
    Create a gzipped SQL dump.

    Returns the path to the created backup file.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    backup_dir = get_backup_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = "_prerestore" if backup_type == BACKUP_TYPE_PRERESTORE else ""
    backup_file = backup_dir / f"market_data_{timestamp}{suffix}.sql.gz"

    conn = sqlite3.connect(str(db_path))
    try:
        with gzip.open(backup_file, "wt", compresslevel=9, encoding="utf-8") as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
    finally:
        conn.close()

    return str(backup_file)


def list_backups() -> list[dict]:
    """
    Return metadata for every backup file (newest first).

    Each entry: {path, filename, date, type, size_bytes, size_mb, legacy}
    """
    backup_dir = get_backup_dir()
    results = []

    for f in sorted(backup_dir.iterdir(), reverse=True):
        m = _FILENAME_RE.match(f.name)
        if m:
            date_str = m.group(1)
            is_prerestore = m.group(2) is not None
            results.append({
                "path": f,
                "filename": f.name,
                "date": date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])),
                "type": BACKUP_TYPE_PRERESTORE if is_prerestore else BACKUP_TYPE_DAILY,
                "size_bytes": f.stat().st_size,
                "size_mb": round(f.stat().st_size / 1_000_000, 1),
                "legacy": False,
            })
            continue

        m = _LEGACY_FILENAME_RE.match(f.name)
        if m:
            date_str = m.group(1)
            results.append({
                "path": f,
                "filename": f.name,
                "date": date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])),
                "type": BACKUP_TYPE_DAILY,
                "size_bytes": f.stat().st_size,
                "size_mb": round(f.stat().st_size / 1_000_000, 1),
                "legacy": True,
            })

    return results


def prune_backups(dry_run: bool = False) -> list[str]:
    """
    Delete backup files (all types) whose date is older than retention_days.

    Returns the list of file paths that were (or would be) removed.
    """
    retention = _retention_days()
    cutoff = date.today() - timedelta(days=retention)
    removed = []

    for entry in list_backups():
        if entry["date"] < cutoff:
            removed.append(str(entry["path"]))
            if not dry_run:
                entry["path"].unlink()

    return removed


def restore_backup(backup_file: str | Path, db_path="data/market_data.db") -> str:
    """
    Restore the database from a backup file.

    Creates a prerestore backup first. Returns the path to that prerestore backup.
    Handles both .sql.gz (new) and .sql (legacy) formats.
    """
    backup_file = Path(backup_file)
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup not found: {backup_file}")

    prerestore_path = create_backup(db_path=db_path, backup_type=BACKUP_TYPE_PRERESTORE)

    if backup_file.suffix == ".gz":
        opener = lambda: gzip.open(backup_file, "rt", encoding="utf-8")
    else:
        opener = lambda: open(backup_file, "r", encoding="utf-8")

    with opener() as f:
        sql = f.read()

    db_path = Path(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(sql)
    finally:
        conn.close()

    return prerestore_path
