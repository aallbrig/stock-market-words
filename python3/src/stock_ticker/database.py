"""
Database operations for the stock ticker CLI.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .config import DB_PATH, SCHEMA_PATH
from .utils import get_today
from .logging_setup import setup_logging

logger = setup_logging()


def get_connection():
    """Create and return a database connection."""
    return sqlite3.connect(DB_PATH)


def init_db(dry_run=False):
    """Initialize the database schema."""
    if dry_run:
        logger.info("DRY RUN: Would initialize database schema")
        logger.info(f"DRY RUN: Would create database at {DB_PATH}")
        logger.info("DRY RUN: Would execute schema.sql")
        return
    
    logger.info("Initializing database schema...")
    
    if not SCHEMA_PATH.exists():
        logger.error(f"Schema file not found: {SCHEMA_PATH}")
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")
    
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()
    
    logger.info("✓ Database schema initialized successfully.")


def ensure_initialized():
    """Ensure database is initialized before running commands."""
    if not DB_PATH.exists():
        logger.info("Database not found. Initializing automatically...")
        init_db()
        return
    
    # Check if tables exist
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    conn.close()
    
    if not tables:
        logger.info("Database exists but is empty. Initializing schema...")
        init_db()


def record_pipeline_step(step_name, tickers_processed=0, status='completed', dry_run=False):
    """Record that a pipeline step was completed."""
    if dry_run:
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    today = get_today()
    
    cursor.execute("""
        INSERT OR REPLACE INTO pipeline_steps (step_name, run_date, completed_at, tickers_processed, status)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
    """, (step_name, today, tickers_processed, status))
    conn.commit()
    conn.close()


def get_step_info(step_name):
    """Get information about when a step was last run."""
    if not DB_PATH.exists():
        return None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        today = get_today()
        
        cursor.execute("""
            SELECT completed_at, tickers_processed, status
            FROM pipeline_steps
            WHERE step_name = ? AND run_date = ?
        """, (step_name, today))
        
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception:
        return None


def get_all_steps_today():
    """Get all steps completed today."""
    if not DB_PATH.exists():
        return []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        today = get_today()
        
        cursor.execute("""
            SELECT step_name, completed_at, tickers_processed, status
            FROM pipeline_steps
            WHERE run_date = ?
            ORDER BY completed_at
        """, (today,))
        
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception:
        return []


def get_last_pipeline_run():
    """Get the timestamp of the last pipeline run."""
    if not DB_PATH.exists():
        return None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(sync_timestamp) FROM sync_history
        """)
        result = cursor.fetchone()
        conn.close()
        return result[0] if result and result[0] else None
    except Exception:
        return None


def recommend_next_step():
    """Recommend the next step based on current progress."""
    if not DB_PATH.exists():
        return "run-all", "Database not initialized. Run full pipeline to start."
    
    conn = get_connection()
    cursor = conn.cursor()
    today = get_today()
    
    # Check if FTP sync is done
    cursor.execute("SELECT sync_date FROM sync_history WHERE sync_date = ?", (today,))
    if not cursor.fetchone():
        conn.close()
        return "sync-ftp", "Download ticker lists from NASDAQ FTP"
    
    # Check if prices extracted
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) FROM daily_metrics 
        WHERE date = ? AND price IS NOT NULL
    """, (today,))
    price_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tickers WHERE is_etf = 0")
    total_tickers = cursor.fetchone()[0]
    
    if price_count == 0:
        conn.close()
        return "extract-prices", "Fetch price/volume data for all tickers (Pass 1)"
    elif price_count < total_tickers:
        conn.close()
        return "extract-prices", f"Resume price extraction ({price_count}/{total_tickers} completed)"
    
    # Check if metadata extracted
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) FROM daily_metrics
        WHERE date = ? AND price >= 5.0 AND volume >= 100000
    """, (today,))
    filtered_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) FROM daily_metrics
        WHERE date = ? AND market_cap IS NOT NULL
    """, (today,))
    metadata_count = cursor.fetchone()[0]
    
    if metadata_count == 0 and filtered_count > 0:
        conn.close()
        return "extract-metadata", f"Fetch detailed metrics for {filtered_count} filtered tickers (Pass 2)"
    elif metadata_count < filtered_count:
        conn.close()
        return "extract-metadata", f"Resume metadata extraction ({metadata_count}/{filtered_count} completed)"
    
    # Check if build is done
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) FROM strategy_scores WHERE date = ?
    """, (today,))
    score_count = cursor.fetchone()[0]
    
    conn.close()
    
    if score_count == 0 and metadata_count > 0:
        return "build", f"Generate JSON assets from {metadata_count} tickers"
    
    # Everything is done
    return None, "✓ All steps completed for today!"


def get_pipeline_state(target_date=None):
    """
    Get the current state of the pipeline for a given date.
    
    Returns: dict with keys:
        - status: 'idle', 'in_progress', 'completed', 'failed', 'partial'
        - current_step: step name if in_progress, else None
        - progress: (current, total) if in_progress, else None
        - completed_steps: list of completed step names
        - recommendation: 'resume', 'restart', or 'run'
    """
    if target_date is None:
        target_date = get_today()
    
    if not DB_PATH.exists():
        return {
            'status': 'idle',
            'current_step': None,
            'progress': None,
            'completed_steps': [],
            'recommendation': 'run'
        }
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check for steps today
    cursor.execute("""
        SELECT step_name, tickers_processed, status, completed_at
        FROM pipeline_steps
        WHERE run_date = ?
        ORDER BY completed_at DESC
    """, (target_date,))
    
    steps = cursor.fetchall()
    
    if not steps:
        conn.close()
        return {
            'status': 'idle',
            'current_step': None,
            'progress': None,
            'completed_steps': [],
            'recommendation': 'run'
        }
    
    # Check for in_progress
    in_progress = [s for s in steps if s[2] == 'in_progress']
    if in_progress:
        step_name, progress, _, _ = in_progress[0]
        # Get total for this step
        total = _get_step_total(step_name, target_date, cursor)
        conn.close()
        return {
            'status': 'in_progress',
            'current_step': step_name,
            'progress': (progress, total),
            'completed_steps': [s[0] for s in steps if s[2] == 'completed'],
            'recommendation': 'resume'
        }
    
    # Check for failed
    failed = [s for s in steps if s[2] == 'failed']
    if failed:
        conn.close()
        return {
            'status': 'failed',
            'current_step': failed[0][0],
            'progress': None,
            'completed_steps': [s[0] for s in steps if s[2] == 'completed'],
            'recommendation': 'restart'
        }
    
    # All completed
    completed_steps = [s[0] for s in steps if s[2] == 'completed']
    all_steps = ['sync-ftp', 'extract-prices', 'extract-metadata', 'build', 'generate-hugo']
    
    conn.close()
    
    if set(completed_steps) >= set(all_steps):
        return {
            'status': 'completed',
            'current_step': None,
            'progress': None,
            'completed_steps': completed_steps,
            'recommendation': 'idle'
        }
    else:
        # Partially completed
        return {
            'status': 'partial',
            'current_step': None,
            'progress': None,
            'completed_steps': completed_steps,
            'recommendation': 'resume'
        }


def _get_step_total(step_name, date, cursor=None):
    """Get the expected total for a step."""
    should_close = False
    if cursor is None:
        conn = get_connection()
        cursor = conn.cursor()
        should_close = True
    
    try:
        if step_name == 'sync-ftp':
            # Total tickers in FTP files
            cursor.execute("SELECT COUNT(*) FROM tickers")
            total = cursor.fetchone()[0]
        elif step_name == 'extract-prices':
            # Non-ETF tickers
            cursor.execute("SELECT COUNT(*) FROM tickers WHERE is_etf = 0")
            total = cursor.fetchone()[0]
        elif step_name == 'extract-metadata':
            # Filtered tickers
            cursor.execute("""
                SELECT COUNT(*) FROM daily_metrics 
                WHERE date = ? AND price >= 5.0 AND volume >= 100000
            """, (date,))
            total = cursor.fetchone()[0]
        elif step_name == 'build':
            # Same as extract-metadata
            cursor.execute("""
                SELECT COUNT(*) FROM daily_metrics 
                WHERE date = ? AND price >= 5.0 AND volume >= 100000 AND market_cap IS NOT NULL
            """, (date,))
            total = cursor.fetchone()[0]
        elif step_name == 'generate-hugo':
            # Number of pages/files generated
            total = 7  # raw-ftp, filtered, 5 strategies
        else:
            total = 0
        
        return total
    finally:
        if should_close:
            conn.close()


def get_step_summary(step_name, run_date=None):
    """
    Get a summary of a completed pipeline step.
    
    Args:
        step_name: Name of the step (e.g., 'sync-ftp', 'extract-prices')
        run_date: Date to query (defaults to today)
    
    Returns:
        dict with step details or None if not found
    """
    if run_date is None:
        run_date = get_today()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT step_name, run_date, completed_at, tickers_processed, status
        FROM pipeline_steps
        WHERE step_name = ? AND run_date = ?
    """, (step_name, run_date))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'step_name': row[0],
            'run_date': row[1],
            'completed_at': row[2],
            'tickers_processed': row[3],
            'status': row[4]
        }
    
    return None


def get_last_successful_run():
    """
    Get the most recent date when the full pipeline completed successfully.
    
    Returns:
        Date string (ISO format) or None if never completed
    """
    if not DB_PATH.exists():
        return None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # A successful run has all required steps completed on the same date
        all_steps = ['sync-ftp', 'extract-prices', 'extract-metadata', 'build', 'generate-hugo']
        
        cursor.execute("""
            SELECT run_date
            FROM pipeline_steps
            WHERE status = 'completed'
            GROUP BY run_date
            HAVING COUNT(DISTINCT step_name) >= 5
            ORDER BY run_date DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    except Exception:
        return None
