"""
Database migration management.
"""
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from .config import DB_PATH, PROJECT_ROOT, PYTHON_DIR
from .database import get_connection
from .logging_setup import setup_logging

logger = setup_logging()

MIGRATIONS_DIR = PYTHON_DIR / "migrations"


def ensure_migrations_table():
    """Create schema_migrations table if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checksum TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def get_migration_files():
    """
    Get all migration files from migrations directory.
    
    Returns:
        List of tuples: (version, filename, full_path)
    """
    if not MIGRATIONS_DIR.exists():
        logger.warning(f"Migrations directory not found: {MIGRATIONS_DIR}")
        return []
    
    migrations = []
    pattern = re.compile(r'^(\d+)_(.+)\.sql$')
    
    for file_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = pattern.match(file_path.name)
        if match:
            version = int(match.group(1))
            description = match.group(2).replace('_', ' ').title()
            migrations.append((version, description, file_path))
    
    return sorted(migrations, key=lambda x: x[0])


def get_applied_migrations():
    """
    Get list of applied migration versions.
    
    Returns:
        Set of version numbers
    """
    if not DB_PATH.exists():
        return set()
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if schema_migrations table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='schema_migrations'
        """)
        
        if not cursor.fetchone():
            conn.close()
            return set()
        
        cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
        versions = {row[0] for row in cursor.fetchall()}
        conn.close()
        return versions
    except Exception as e:
        logger.debug(f"Error getting applied migrations: {e}")
        return set()


def get_pending_migrations():
    """
    Get migrations that haven't been applied yet.
    
    Returns:
        List of tuples: (version, description, file_path)
    """
    all_migrations = get_migration_files()
    applied = get_applied_migrations()
    
    return [m for m in all_migrations if m[0] not in applied]


def apply_migration(version, description, file_path):
    """
    Apply a single migration file.
    
    Args:
        version: Migration version number
        description: Migration description
        file_path: Path to migration SQL file
    """
    logger.info(f"Applying migration {version:03d}: {description}")
    
    with open(file_path, 'r') as f:
        sql = f.read()
    
    # Remove leading comment lines but keep SQL statements
    lines = sql.split('\n')
    sql_lines = []
    started_sql = False
    
    for line in lines:
        stripped = line.strip()
        # Start collecting once we hit a non-comment line
        if not started_sql:
            if stripped and not stripped.startswith('--'):
                started_sql = True
                sql_lines.append(line)
        else:
            sql_lines.append(line)
    
    sql = '\n'.join(sql_lines).strip()
    
    if not sql:
        logger.warning(f"No SQL statements found in migration {version:03d}, skipping")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Execute migration SQL
        cursor.executescript(sql)
        
        # Record migration
        cursor.execute("""
            INSERT INTO schema_migrations (version, description)
            VALUES (?, ?)
        """, (version, description))
        
        conn.commit()
        logger.info(f"✓ Migration {version:03d} applied successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"✗ Migration {version:03d} failed: {e}")
        raise
    finally:
        conn.close()


def rollback_migration(version, description):
    """
    Rollback a migration (remove from schema_migrations table).
    
    Note: SQLite limitations mean we can't actually revert ALTER TABLE ADD COLUMN.
    This just marks the migration as not applied.
    """
    logger.warning(f"Rolling back migration {version:03d}: {description}")
    logger.warning("Note: SQLite doesn't support DROP COLUMN - this only removes the migration record")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DELETE FROM schema_migrations WHERE version = ?
        """, (version,))
        
        conn.commit()
        logger.info(f"✓ Migration {version:03d} record removed")
    except Exception as e:
        conn.rollback()
        logger.error(f"✗ Rollback failed: {e}")
        raise
    finally:
        conn.close()


def migrate_up():
    """Apply all pending migrations."""
    ensure_migrations_table()
    
    pending = get_pending_migrations()
    
    if not pending:
        logger.info("✓ Database is up to date - no pending migrations")
        return
    
    logger.info(f"Found {len(pending)} pending migration(s)")
    
    for version, description, file_path in pending:
        apply_migration(version, description, file_path)
    
    logger.info(f"✓ Applied {len(pending)} migration(s) successfully")


def migrate_down():
    """Rollback the most recent migration."""
    ensure_migrations_table()
    
    applied = get_applied_migrations()
    
    if not applied:
        logger.warning("No migrations to rollback")
        return
    
    # Get most recent migration
    latest_version = max(applied)
    
    # Find its description
    all_migrations = get_migration_files()
    description = None
    for v, desc, _ in all_migrations:
        if v == latest_version:
            description = desc
            break
    
    if description is None:
        description = "Unknown"
    
    rollback_migration(latest_version, description)


def migration_status():
    """
    Get detailed migration status.
    
    Returns:
        dict with keys: pending, applied, total
    """
    all_migrations = get_migration_files()
    applied = get_applied_migrations()
    
    status = {
        'total': len(all_migrations),
        'applied': len(applied),
        'pending': len(all_migrations) - len(applied),
        'migrations': []
    }
    
    for version, description, file_path in all_migrations:
        is_applied = version in applied
        status['migrations'].append({
            'version': version,
            'description': description,
            'applied': is_applied,
            'file': file_path.name
        })
    
    return status


def check_migrations_needed():
    """
    Quick check if migrations are needed.
    
    Returns:
        bool: True if pending migrations exist
    """
    all_migrations = get_migration_files()
    applied = get_applied_migrations()
    
    return len(all_migrations) > len(applied)
