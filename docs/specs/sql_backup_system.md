# SQL Backup System

**Status:** Draft
**Author:** Copilot
**Created:** 2026-04-10
**Supersedes:** (none)
**Superseded by:** (none)

## Context

The stock-market-words project uses a SQLite database (`data/market_data.db`) to persist state between CLI runs. This database contains critical market data, ticker scores, and strategy information used by the Hugo site. Currently, there is no backup mechanism, which creates risk:

- Data loss from corruption or accidental deletion
- No recovery point before running migrations
- No audit trail of historical database states
- Deployment uncertainty around data integrity

Operators running `ticker-cli` need a way to safely back up data before destructive operations like migrations, and developers need on-demand backup capability for testing and debugging.

## Goal

Provide automated pre-migration backups and on-demand CLI commands to reliably back up the SQLite database with timestamped SQL dump files stored in a versioned backup directory.

## Non-goals

- Incremental backups or snapshot-based restore (full database dumps only)
- Remote/cloud backup storage (local filesystem only)
- Backup retention policies or auto-cleanup (keep all backups indefinitely)
- Restore functionality (out of scope; users can manually restore SQL dumps)
- Compression or encryption (plain SQL files for simplicity)

## User stories

- As an operator, I want `ticker-cli backup` to create a point-in-time backup of the database before running risky operations, so I can recover if something goes wrong.
- As a developer, I want backups to be automatically created before migrations run, so I never have to worry about losing data during schema updates.
- As a site maintainer, I want to inspect backup timestamps and file sizes to understand when the last database snapshot was taken, so I can verify my deployment safety.
- As a developer running tests or in development, I want `ticker-cli migration up --skip-backup` to skip backup creation (with a warning), so I can iterate faster during testing without filling the backup directory.

## Design

### Architecture

A new `backup` root-level command added to the Click CLI in `python3/src/stock_ticker/cli.py`, with a backing utility module for common backup logic used both by the CLI and by the migration system.

**New files to create:**

1. `python3/src/stock_ticker/backup.py` — Core backup utility
   - `create_backup(db_path, backup_dir)` — Returns path to newly created backup file
   - `get_backup_dir()` — Ensures backup directory exists, returns path
   - Uses SQLite `.dump` command via `sqlite3` module

**Existing files to modify:**

1. `python3/src/stock_ticker/cli.py` — Main CLI entry point
   - Add `@cli.command()` decorator for new `backup()` function
   - Add `--db-path` option with default `data/market_data.db`
   - Import and call `backup.create_backup()`
   - Add `--skip-backup` flag to existing `migrate_up_cmd()` function

2. `python3/src/stock_ticker/migrations.py` (or wherever migrations are defined)
   - Add pre-migration hook in the `migrate_up()` function
   - Call `backup.create_backup()` before any migration runs
   - Log backup path to console/migration log
   - If backup creation fails, halt the migration with clear error
   - Support `skip_backup` parameter to skip backup creation

### Backup file naming

**Format:** `market_data_YYYYMMDD_HHMMSS.sql`

**Example:** `market_data_20260410_010430.sql` (April 10, 2026, 01:04:30 UTC)

**Location:** `data/backups/` (created if it doesn't exist)

### Backup storage structure

```
data/
├── market_data.db
└── backups/
    ├── market_data_20260408_150000.sql
    ├── market_data_20260408_160000.sql
    ├── market_data_20260409_050000.sql
    └── market_data_20260410_010430.sql
```

### Implementation details

**Python backup utility (`backup.py`):**

```python
import sqlite3
import os
from pathlib import Path
from datetime import datetime

def get_backup_dir(base_path="data"):
    """Ensure backup directory exists and return its path."""
    backup_dir = Path(base_path) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def create_backup(db_path="data/market_data.db", backup_dir=None):
    """
    Create a timestamped SQL dump of the database.
    
    Returns:
        str: Path to the created backup file
        
    Raises:
        FileNotFoundError: If database file doesn't exist
        sqlite3.Error: If backup creation fails
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    if backup_dir is None:
        backup_dir = get_backup_dir()
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"market_data_{timestamp}.sql"
    
    # Connect to database and dump to SQL file
    conn = sqlite3.connect(db_path)
    with open(backup_file, 'w') as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    conn.close()
    
    return str(backup_file)
```

**CLI backup command (`cli.py`):**

```python
@cli.command()
@click.option('--db-path', default='data/market_data.db', 
              help='Path to SQLite database file')
@log_timing
def backup(db_path):
    """Create a backup of the SQLite database."""
    from .backup import create_backup
    
    logger.info("=" * 70)
    logger.info("=== 💾 DATABASE BACKUP ===")
    logger.info("=" * 70)
    logger.info("")
    
    try:
        backup_path = create_backup(db_path=db_path)
        logger.info(f"✓ Backup created: {backup_path}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"✗ Backup failed: {e}")
        sys.exit(1)
```

**Migration integration (`migrations.py`):**

```python
from .backup import create_backup

def migrate_up(skip_backup=False):
    """Run pending migrations with optional pre-migration backup."""
    if not skip_backup:
        try:
            backup_path = create_backup()
            logger.info(f"Pre-migration backup: {backup_path}")
        except Exception as e:
            logger.error(f"CRITICAL: Could not create pre-migration backup: {e}")
            sys.exit(1)
    else:
        logger.warning("⚠️  WARNING: Skipping pre-migration backup (--skip-backup used)")
    
    # Run the actual migrations...
```

**Migration up command with `--skip-backup` flag (`cli.py`):**

```python
@migrate.command('up')
@click.option('--skip-backup', is_flag=True,
              help='Skip pre-migration backup creation')
@log_timing
def migrate_up_cmd(skip_backup):
    """Apply all pending migrations."""
    logger.info("=" * 70)
    logger.info("=== 🔼 APPLYING MIGRATIONS ===")
    logger.info("=" * 70)
    logger.info("")
    
    try:
        from .migrations import migrate_up
        migrate_up(skip_backup=skip_backup)
        logger.info("")
        logger.info("✓ All migrations applied successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        sys.exit(1)
```

## Affected files

- `python3/src/stock_ticker/backup.py` (new)
- `python3/src/stock_ticker/cli.py` (modify: add `backup()` command, add `--skip-backup` flag to `migrate_up_cmd()`)
- `python3/src/stock_ticker/migrations.py` (modify: add pre-migration backup hook, accept `skip_backup` parameter)
- `data/backups/.gitkeep` (new, to track directory in git)

## Verification

**Manual verification:**

1. CLI command works:
   ```bash
   cd /home/aallbright/src/stock-market-words
   python3/ticker-cli backup
   # Expected: ✓ Backup created: data/backups/market_data_YYYYMMDD_HHMMSS.sql
   ls -la data/backups/
   # Expected: SQL file exists with correct timestamp
   ```

2. Pre-migration backup is created:
   - Modify a table definition in the database
   - Run `ticker-cli migration up`
   - Verify `data/backups/` contains a new `.sql` file
   - Verify timestamp is before the migration ran

3. Skip backup flag works:
   - Run `ticker-cli migration up --skip-backup`
   - Verify ⚠️ warning message appears in output
   - Verify no new backup file is created in `data/backups/`

4. Backup integrity:
   - Restore from a backup file to a test database
   - Verify tables and row counts match the original

**Automated verification:**

- Create `tests/backup.test.py` (or add to existing test file):
  - `test_backup_creates_file()` — verify file is created in correct location
  - `test_backup_filename_format()` — verify timestamp format is correct
  - `test_backup_contains_sql()` — verify output is valid SQL with CREATE TABLE statements
  - `test_pre_migration_backup()` — verify backup is created before migration runs
  - `test_skip_backup_flag()` — verify `--skip-backup` prevents backup creation
  - `test_skip_backup_warning()` — verify warning message is printed when using `--skip-backup`

**Data verification:**

- Query a restored database: `SELECT COUNT(*) FROM tickers;` should match original
- Verify backup file is valid SQL by running: `sqlite3 :memory: < backup_file.sql`

## Open questions

1. **Database path configurability**: Should the database path be configurable via CLI flag or environment variable?
   - Default answer: Use `args.db_path` CLI flag with fallback to `data/market_data.db`

2. **Verbose output**: Should backup creation print metadata (file size, table count)?
   - Default answer: Just print the path and mark as done with `✓`. Operators can `ls -lh` for details.

3. **Error handling during migrations**: If pre-migration backup fails, should the migration be skipped or continue?
   - Default answer: **Fail hard** — don't proceed with migrations if backup creation fails. This is safer.

4. **Backup ownership/permissions**: Should backups be readable by the web server user?
   - Default answer: Use OS defaults. Assume the ticker-cli and web server share the same user or group.

5. **Skip backup flag for all commands**: Should `--skip-backup` apply only to `migration up`, or to the `backup` command as well?
   - Default answer: `--skip-backup` only applies to migrations. The `backup` command always creates a backup or errors.

6. **Short flag for --skip-backup**: Should there be a short flag like `-B`?
   - Default answer: No short flag. Explicit `--skip-backup` is better — discourages accidental usage.

## Alternatives considered

1. **Use `mysqldump` or `pg_dump`** — Not applicable; this project uses SQLite.

2. **Compressed backups (gzip)** — Rejected to keep it simple for now. SQL files compress well (~80% ratio), but adding complexity doesn't justify the storage savings at this scale.

3. **Retention policies (auto-delete old backups)** — Rejected per non-goals. Disk space for SQL dumps is cheap; operators can manually clean up if needed.

4. **Built-in restore command** — Rejected (out of scope). Restoring is rare and inherently risky; better to make operators think about it rather than provide easy automation.

5. **Backup to cloud storage (S3, GCS)** — Rejected per non-goals. Local filesystem is simpler and sufficient for this use case. Can be added later if needed.
