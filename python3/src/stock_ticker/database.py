"""
Database operations for the stock ticker CLI.
"""
import sqlite3
import re
from datetime import datetime, timezone
from pathlib import Path
from .config import DB_PATH, SCHEMA_PATH
from .utils import get_today
from .logging_setup import setup_logging

logger = setup_logging()


def get_expected_tables_from_schema():
    """
    Parse schema.sql and extract all table names dynamically.
    
    Returns:
        list: Table names defined in the schema file
    """
    # Ensure SCHEMA_PATH is a Path object
    schema_path = Path(SCHEMA_PATH) if isinstance(SCHEMA_PATH, str) else SCHEMA_PATH
    
    if not schema_path.exists():
        logger.warning(f"Schema file not found at {schema_path}")
        return []
    
    with open(schema_path, 'r') as f:
        schema_content = f.read()
    
    # Pattern to match CREATE TABLE statements
    # Matches: CREATE TABLE IF NOT EXISTS tablename
    # Also matches: CREATE TABLE tablename
    pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)'
    
    table_names = re.findall(pattern, schema_content, re.IGNORECASE)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tables = []
    for table in table_names:
        if table not in seen:
            seen.add(table)
            unique_tables.append(table)
    
    logger.debug(f"Parsed {len(unique_tables)} tables from schema: {', '.join(unique_tables)}")
    return unique_tables


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
            SELECT MAX(completed_at) FROM pipeline_runs
            WHERE status = 'completed'
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


def reset_pipeline_state(target_date=None):
    """
    Reset the pipeline state for a given date by deleting all pipeline_steps records.
    This allows --force to re-run the pipeline from scratch.
    """
    if target_date is None:
        target_date = get_today()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM pipeline_steps
        WHERE run_date = ?
    """, (target_date,))
    
    conn.commit()
    conn.close()
    
    logger.info(f"Pipeline state reset for {target_date}")


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


def create_pipeline_run(run_date, nasdaq_ftp_reachable=None, yahoo_finance_reachable=None):
    """
    Create a new pipeline run record.
    
    Args:
        run_date: Date of the pipeline run
        nasdaq_ftp_reachable: Whether NASDAQ FTP was reachable (optional)
        yahoo_finance_reachable: Whether Yahoo Finance API was reachable (optional)
    
    Returns:
        int: run_id of the created record
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO pipeline_runs (
            run_date, started_at, status,
            nasdaq_ftp_reachable, yahoo_finance_reachable
        ) VALUES (?, CURRENT_TIMESTAMP, 'pending', ?, ?)
    """, (run_date, nasdaq_ftp_reachable, yahoo_finance_reachable))
    
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return run_id


def update_pipeline_run(run_id, status='completed', failed_step=None, metrics=None, timings=None):
    """
    Update a pipeline run record with final status and metrics.
    
    Args:
        run_id: ID of the pipeline run
        status: Final status ('completed', 'failed')
        failed_step: Name of step that failed (if applicable)
        metrics: Dict with keys: total_requests, total_failures, total_bytes_downloaded,
                 tickers_processed_prices, tickers_processed_metadata
        timings: Dict with keys: sync_ftp, extract_prices, extract_metadata, build, 
                 generate_hugo, total
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = ['completed_at = CURRENT_TIMESTAMP', 'status = ?']
    params = [status]
    
    if failed_step:
        updates.append('failed_step = ?')
        params.append(failed_step)
    
    if metrics:
        if 'total_requests' in metrics:
            updates.append('total_requests = ?')
            params.append(metrics['total_requests'])
        if 'total_failures' in metrics:
            updates.append('total_failures = ?')
            params.append(metrics['total_failures'])
        if 'total_bytes_downloaded' in metrics:
            updates.append('total_bytes_downloaded = ?')
            params.append(metrics['total_bytes_downloaded'])
        if 'tickers_processed_prices' in metrics:
            updates.append('tickers_processed_prices = ?')
            params.append(metrics['tickers_processed_prices'])
        if 'tickers_processed_metadata' in metrics:
            updates.append('tickers_processed_metadata = ?')
            params.append(metrics['tickers_processed_metadata'])
    
    if timings:
        if 'sync_ftp' in timings:
            updates.append('timing_sync_ftp = ?')
            params.append(timings['sync_ftp'])
        if 'extract_prices' in timings:
            updates.append('timing_extract_prices = ?')
            params.append(timings['extract_prices'])
        if 'extract_metadata' in timings:
            updates.append('timing_extract_metadata = ?')
            params.append(timings['extract_metadata'])
        if 'build' in timings:
            updates.append('timing_build = ?')
            params.append(timings['build'])
        if 'generate_hugo' in timings:
            updates.append('timing_generate_hugo = ?')
            params.append(timings['generate_hugo'])
        if 'total' in timings:
            updates.append('timing_total = ?')
            params.append(timings['total'])
    
    params.append(run_id)
    
    query = f"UPDATE pipeline_runs SET {', '.join(updates)} WHERE run_id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()


def batch_create_ticker_sync_records(run_id, sync_type, symbols, batch_number):
    """
    Create pending ticker sync records for a batch.
    
    Args:
        run_id: ID of the pipeline run
        sync_type: 'price' or 'metadata'
        symbols: List of ticker symbols
        batch_number: Batch number for this group of tickers
    
    Returns:
        List of created record IDs
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    records = [
        (run_id, sync_type, symbol, batch_number, 'pending')
        for symbol in symbols
    ]
    
    cursor.executemany("""
        INSERT INTO ticker_sync_history (
            run_id, sync_type, symbol, batch_number, started_at, status
        ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
    """, records)
    
    conn.commit()
    
    # Get the IDs of created records
    cursor.execute("""
        SELECT id FROM ticker_sync_history
        WHERE run_id = ? AND sync_type = ? AND batch_number = ?
        ORDER BY id DESC
        LIMIT ?
    """, (run_id, sync_type, batch_number, len(symbols)))
    
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return ids


def batch_update_ticker_sync_records(run_id, sync_type, batch_number, successful_symbols, 
                                      failed_symbols_with_errors, bytes_per_ticker=None):
    """
    Update ticker sync records after batch completes.
    
    Args:
        run_id: ID of the pipeline run
        sync_type: 'price' or 'metadata'
        batch_number: Batch number
        successful_symbols: List of symbols that succeeded
        failed_symbols_with_errors: Dict of {symbol: error_message} for failures
        bytes_per_ticker: Dict of {symbol: bytes_downloaded} (optional)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Update successful symbols
    if successful_symbols:
        for symbol in successful_symbols:
            bytes_downloaded = bytes_per_ticker.get(symbol, 0) if bytes_per_ticker else 0
            cursor.execute("""
                UPDATE ticker_sync_history
                SET completed_at = CURRENT_TIMESTAMP,
                    status = 'success',
                    bytes_downloaded = ?
                WHERE run_id = ? AND sync_type = ? AND symbol = ? AND batch_number = ?
            """, (bytes_downloaded, run_id, sync_type, symbol, batch_number))
    
    # Update failed symbols
    for symbol, error_msg in failed_symbols_with_errors.items():
        cursor.execute("""
            UPDATE ticker_sync_history
            SET completed_at = CURRENT_TIMESTAMP,
                status = 'failed',
                error_message = ?
            WHERE run_id = ? AND sync_type = ? AND symbol = ? AND batch_number = ?
        """, (error_msg, run_id, sync_type, symbol, batch_number))
    
    conn.commit()
    conn.close()


def get_ticker_sync_failures(run_id=None, sync_type=None, limit=100):
    """
    Get ticker sync failures for a specific run or globally.
    
    Args:
        run_id: Optional pipeline run ID to filter by
        sync_type: Optional sync type ('price' or 'metadata') to filter by
        limit: Maximum number of results to return
    
    Returns:
        List of dicts with failure information
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            tsh.symbol,
            tsh.sync_type,
            tsh.completed_at,
            tsh.error_message,
            pr.run_date
        FROM ticker_sync_history tsh
        JOIN pipeline_runs pr ON tsh.run_id = pr.run_id
        WHERE tsh.status = 'failed'
    """
    params = []
    
    if run_id:
        query += " AND tsh.run_id = ?"
        params.append(run_id)
    
    if sync_type:
        query += " AND tsh.sync_type = ?"
        params.append(sync_type)
    
    query += " ORDER BY tsh.completed_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'symbol': row[0],
            'sync_type': row[1],
            'completed_at': row[2],
            'error_message': row[3],
            'run_date': row[4]
        }
        for row in rows
    ]


def clean_today_data(step_name=None, target_date=None, dry_run=False):
    """
    Clean today's data for a specific step or all steps.
    
    This function removes data for today only, never previous days.
    Used with --clean flag to reset the pipeline for a fresh run.
    
    Args:
        step_name: Optional step name to clean ('sync-ftp', 'extract-prices', 
                   'extract-metadata', 'build', 'generate-hugo', or None for all)
        target_date: Date to clean (defaults to today)
        dry_run: If True, only log what would be deleted
    
    Returns:
        dict with counts of deleted records
    """
    if target_date is None:
        target_date = get_today()
    
    logger.info(f"Cleaning data for {target_date}" + 
                (f" (step: {step_name})" if step_name else " (all steps)"))
    
    conn = get_connection()
    cursor = conn.cursor()
    
    counts = {
        'ticker_sync_history': 0,
        'pipeline_runs': 0,
        'strategy_scores': 0,
        'daily_metrics': 0,
        'pipeline_steps': 0
    }
    
    if dry_run:
        logger.info("DRY RUN: Would delete the following:")
        
        # Check what would be deleted
        if step_name is None or step_name in ['extract-prices', 'extract-metadata']:
            cursor.execute("""
                SELECT COUNT(*) FROM ticker_sync_history 
                WHERE run_id IN (SELECT run_id FROM pipeline_runs WHERE run_date = ?)
            """, (target_date,))
            counts['ticker_sync_history'] = cursor.fetchone()[0]
        
        if step_name is None:
            cursor.execute("SELECT COUNT(*) FROM pipeline_runs WHERE run_date = ?", (target_date,))
            counts['pipeline_runs'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM strategy_scores WHERE date = ?", (target_date,))
            counts['strategy_scores'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = ?", (target_date,))
            counts['daily_metrics'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM pipeline_steps WHERE run_date = ?", (target_date,))
            counts['pipeline_steps'] = cursor.fetchone()[0]
        elif step_name == 'build':
            cursor.execute("SELECT COUNT(*) FROM strategy_scores WHERE date = ?", (target_date,))
            counts['strategy_scores'] = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM pipeline_steps 
                WHERE run_date = ? AND step_name = ?
            """, (target_date, step_name))
            counts['pipeline_steps'] = cursor.fetchone()[0]
        elif step_name in ['extract-prices', 'extract-metadata']:
            cursor.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = ?", (target_date,))
            counts['daily_metrics'] = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM pipeline_steps 
                WHERE run_date = ? AND step_name = ?
            """, (target_date, step_name))
            counts['pipeline_steps'] = cursor.fetchone()[0]
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM pipeline_steps 
                WHERE run_date = ? AND step_name = ?
            """, (target_date, step_name))
            counts['pipeline_steps'] = cursor.fetchone()[0]
        
        for table, count in counts.items():
            if count > 0:
                logger.info(f"  • {table}: {count} records")
        
        conn.close()
        return counts
    
    # Perform actual deletion
    if step_name is None:
        # Clean everything for today
        logger.info("  Deleting ticker_sync_history...")
        cursor.execute("""
            DELETE FROM ticker_sync_history 
            WHERE run_id IN (SELECT run_id FROM pipeline_runs WHERE run_date = ?)
        """, (target_date,))
        counts['ticker_sync_history'] = cursor.rowcount
        
        logger.info("  Deleting pipeline_runs...")
        cursor.execute("DELETE FROM pipeline_runs WHERE run_date = ?", (target_date,))
        counts['pipeline_runs'] = cursor.rowcount
        
        logger.info("  Deleting strategy_scores...")
        cursor.execute("DELETE FROM strategy_scores WHERE date = ?", (target_date,))
        counts['strategy_scores'] = cursor.rowcount
        
        logger.info("  Deleting daily_metrics...")
        cursor.execute("DELETE FROM daily_metrics WHERE date = ?", (target_date,))
        counts['daily_metrics'] = cursor.rowcount
        
        logger.info("  Deleting pipeline_steps...")
        cursor.execute("DELETE FROM pipeline_steps WHERE run_date = ?", (target_date,))
        counts['pipeline_steps'] = cursor.rowcount
        
    elif step_name == 'sync-ftp':
        # Clean only the pipeline step record (ticker data stays)
        logger.info("  Deleting pipeline_steps for sync-ftp...")
        cursor.execute("""
            DELETE FROM pipeline_steps 
            WHERE run_date = ? AND step_name = ?
        """, (target_date, step_name))
        counts['pipeline_steps'] = cursor.rowcount
        
    elif step_name in ['extract-prices', 'extract-metadata']:
        # Clean daily_metrics, ticker_sync_history for this step, and pipeline_steps
        logger.info(f"  Deleting ticker_sync_history for {step_name}...")
        sync_type = 'price' if step_name == 'extract-prices' else 'metadata'
        cursor.execute("""
            DELETE FROM ticker_sync_history 
            WHERE run_id IN (SELECT run_id FROM pipeline_runs WHERE run_date = ?)
            AND sync_type = ?
        """, (target_date, sync_type))
        counts['ticker_sync_history'] = cursor.rowcount
        
        logger.info(f"  Deleting daily_metrics for {target_date}...")
        cursor.execute("DELETE FROM daily_metrics WHERE date = ?", (target_date,))
        counts['daily_metrics'] = cursor.rowcount
        
        logger.info(f"  Deleting pipeline_steps for {step_name}...")
        cursor.execute("""
            DELETE FROM pipeline_steps 
            WHERE run_date = ? AND step_name = ?
        """, (target_date, step_name))
        counts['pipeline_steps'] = cursor.rowcount
        
    elif step_name == 'build':
        # Clean strategy_scores and pipeline_steps
        logger.info("  Deleting strategy_scores...")
        cursor.execute("DELETE FROM strategy_scores WHERE date = ?", (target_date,))
        counts['strategy_scores'] = cursor.rowcount
        
        logger.info("  Deleting pipeline_steps for build...")
        cursor.execute("""
            DELETE FROM pipeline_steps 
            WHERE run_date = ? AND step_name = ?
        """, (target_date, step_name))
        counts['pipeline_steps'] = cursor.rowcount
        
    elif step_name == 'generate-hugo':
        # Clean only pipeline_steps (Hugo files stay on disk)
        logger.info("  Deleting pipeline_steps for generate-hugo...")
        cursor.execute("""
            DELETE FROM pipeline_steps 
            WHERE run_date = ? AND step_name = ?
        """, (target_date, step_name))
        counts['pipeline_steps'] = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    logger.info("✓ Data cleaned successfully")
    for table, count in counts.items():
        if count > 0:
            logger.info(f"  • {table}: {count} records deleted")
    
    return counts
