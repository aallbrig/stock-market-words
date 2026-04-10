"""
Click-based CLI for the stock ticker application.
"""
import sys
import click
import time
from datetime import datetime, timezone
from pathlib import Path
from functools import wraps

from .logging_setup import setup_logging
from .config import DB_PATH, API_DIR, ERROR_LOG_PATH, FTP_HOST, YAHOO_API_HOST
from .database import (
    init_db, ensure_initialized, get_connection, 
    get_all_steps_today, get_last_pipeline_run, recommend_next_step,
    clean_today_data
)
from .migrations import (
    check_migrations_needed, migrate_up, migrate_down, 
    migration_status, ensure_migrations_table
)
from .ftp_sync import sync_ftp
from .extractors import extract_prices, extract_metadata
from .builders import build_assets
from .hugo_generators import (
    generate_raw_ftp_data, 
    generate_filtered_data, 
    generate_strategy_filters,
    generate_hugo_pages,
    generate_all_tickers_json,
    generate_all_hugo_content
)
from .utils import get_today, check_ftp_server, check_yahoo_finance
from .retry import get_request_metrics
from .translate import TranslateConfig, run_translate

logger = setup_logging()


def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m ({seconds:.0f}s)"
    else:
        hours = seconds / 3600
        minutes = (seconds % 3600) / 60
        return f"{hours:.1f}h ({minutes:.0f}m)"


def log_timing(func):
    """Decorator to log execution time of commands."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info("")
            logger.info(f"⏱️  Command completed in {format_duration(elapsed)}")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("")
            logger.error(f"⏱️  Command failed after {format_duration(elapsed)}")
            raise
    return wrapper


class Context:
    """Shared context for CLI commands."""
    def __init__(self):
        self.dry_run = False


@click.group()
@click.option('--dry-run', is_flag=True, help='Simulate actions without making changes')
@click.pass_context
def cli(ctx, dry_run):
    """
    Stock Market Ticker Discovery CLI
    
    Manages extraction, filtering, and processing of stock market data.
    """
    ctx.obj = Context()
    ctx.obj.dry_run = dry_run
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")


@cli.command()
@log_timing
def status():
    """Check system readiness and pipeline status."""
    logger.info("=" * 70)
    logger.info("=== 📊 SYSTEM STATUS ===")
    logger.info("=" * 70)
    logger.info("")
    
    # Track various issues for exit code
    missing_deps = []
    unreachable_services = []
    db_issue_reason = None  # None, "schema_missing", "tables_incomplete", "migrations_pending", "connection_error"
    
    # 1. DATA OVERVIEW
    logger.info("1️⃣  DATA OVERVIEW")
    
    if not DB_PATH.exists():
        logger.warning("   ⚠ No database found")
        logger.info("")
    else:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get latest date
            cursor.execute("SELECT MAX(date) FROM daily_metrics")
            latest_date = cursor.fetchone()[0]
            
            if latest_date:
                # Count unique active tickers
                cursor.execute("""
                    SELECT COUNT(DISTINCT symbol) 
                    FROM daily_metrics 
                    WHERE date = ?
                """, (latest_date,))
                active_tickers = cursor.fetchone()[0]
                
                # Get database file size
                import os
                db_bytes = os.path.getsize(DB_PATH)
                db_mb = db_bytes / (1024 * 1024)
                
                # Count tickers with metadata (those with sector info)
                cursor.execute("""
                    SELECT COUNT(DISTINCT dm.symbol)
                    FROM daily_metrics dm
                    JOIN tickers t ON dm.symbol = t.symbol
                    WHERE dm.date = ? AND t.sector IS NOT NULL
                """, (latest_date,))
                metadata_tickers = cursor.fetchone()[0]
                
                # Get sector breakdown
                cursor.execute("""
                    SELECT t.sector, COUNT(DISTINCT dm.symbol) as count
                    FROM daily_metrics dm
                    JOIN tickers t ON dm.symbol = t.symbol
                    WHERE dm.date = ? AND t.sector IS NOT NULL
                    GROUP BY t.sector
                    ORDER BY count DESC
                """, (latest_date,))
                sectors = cursor.fetchall()
                
                logger.info(f"   Latest data: {latest_date}")
                logger.info(f"   Active tickers: {active_tickers:,}")
                logger.info(f"   Database size: {db_mb:.1f} MB ({db_bytes:,} bytes)")
                logger.info(f"   Tickers with metadata: {metadata_tickers:,}")
                
                if sectors:
                    logger.info("   Sector breakdown:")
                    for sector, count in sectors:
                        percentage = (count / metadata_tickers * 100) if metadata_tickers > 0 else 0
                        logger.info(f"      • {sector}: {count:,} ({percentage:.1f}%)")
            else:
                logger.warning("   ⚠ No data in database yet")
            
            conn.close()
        except Exception as e:
            logger.warning(f"   ⚠ Error reading data: {e}")
    
    logger.info("")
    
    # 2. DEPENDENCIES CHECK
    logger.info("2️⃣  DEPENDENCIES")
    
    # Database
    if not DB_PATH.exists():
        logger.warning("   ⚠ Database: NOT FOUND")
        logger.warning(f"   → Database file expected at: {DB_PATH}")
        logger.warning("   → Initialize database with: python -m stock_ticker.cli init")
        db_issue_reason = "schema_missing"
    else:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check if sqlite3 command is available
            import shutil
            if not shutil.which('sqlite3'):
                logger.warning("   ⚠ sqlite3 command-line tool: NOT FOUND")
                logger.warning("   → Install with: sudo apt-get install sqlite3 (Debian/Ubuntu)")
                logger.warning("   → Or: brew install sqlite (macOS)")
           
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                logger.warning("   ⚠ Database: Schema not initialized")
                logger.warning(f"   → Database file exists but has no tables")
                logger.warning("   → Initialize schema with: python -m stock_ticker.cli init")
                db_issue_reason = "schema_missing"
            else:
                # Check if all expected tables exist (dynamically parsed from schema.sql)
                from .database import get_expected_tables_from_schema
                expected_tables = get_expected_tables_from_schema()
                
                if not expected_tables:
                    # Fallback if schema parsing fails
                    logger.warning("   ⚠ Could not parse schema file for expected tables")
                    logger.info(f"   ✓ Database: Ready ({len(tables)} tables)")
                else:
                    missing_tables = [t for t in expected_tables if t not in tables]
                    
                    if missing_tables:
                        logger.warning(f"   ⚠ Database: Missing tables: {', '.join(missing_tables)}")
                        logger.warning("   → Reinitialize schema with: python -m stock_ticker.cli init")
                        db_issue_reason = "tables_incomplete"
                    else:
                        logger.info(f"   ✓ Database: Ready ({len(tables)} tables)")
                
                # Check for pending migrations
                if check_migrations_needed():
                    logger.warning("   ⚠️  Database migrations pending!")
                    logger.warning("   → Run migrations with: python -m stock_ticker.cli migrate up")
                    db_issue_reason = "migrations_pending"
                else:
                    # Check if schema was recently updated (migrations applied today)
                    cursor.execute("""
                        SELECT COUNT(*) FROM schema_migrations 
                        WHERE DATE(applied_at) = DATE('now')
                    """)
                    recent_migrations = cursor.fetchone()[0]
                    
                    if recent_migrations > 0:
                        logger.info(f"   ℹ️  Schema updated today ({recent_migrations} migration(s) applied)")
                        logger.info("   💡 Re-run extract-metadata to populate new fields")
            
            conn.close()
        except Exception as e:
            logger.warning(f"   ⚠ Database: Error connecting ({e})")
            logger.warning(f"   → Check database file permissions: {DB_PATH}")
            logger.warning("   → Try reinitializing: python -m stock_ticker.cli init")
            db_issue_reason = "connection_error"
    
    # Python packages
    try:
        import yfinance
        logger.info(f"   ✓ yfinance: {yfinance.__version__}")
    except ImportError:
        logger.warning("   ⚠ yfinance: NOT INSTALLED")
        missing_deps.append('yfinance')
    
    try:
        import pandas as pd
        logger.info(f"   ✓ pandas: {pd.__version__}")
    except ImportError:
        logger.warning("   ⚠ pandas: NOT INSTALLED")
        missing_deps.append('pandas')
    
    try:
        import numpy
        logger.info(f"   ✓ numpy: {numpy.__version__}")
    except ImportError:
        logger.warning("   ⚠ numpy: NOT INSTALLED")
        missing_deps.append('numpy')
    
    # External services
    ftp_reachable = check_ftp_server(FTP_HOST)
    if ftp_reachable:
        logger.info(f"   ✓ NASDAQ FTP: Reachable ({FTP_HOST})")
    else:
        logger.warning(f"   ⚠ NASDAQ FTP: Unreachable ({FTP_HOST})")
        unreachable_services.append('NASDAQ FTP')
    
    yahoo_reachable = check_yahoo_finance(YAHOO_API_HOST)
    if yahoo_reachable:
        logger.info(f"   ✓ Yahoo Finance API: Reachable ({YAHOO_API_HOST})")
    else:
        logger.warning(f"   ⚠ Yahoo Finance API: Unreachable ({YAHOO_API_HOST})")
        unreachable_services.append('Yahoo Finance API')
    
    logger.info("")
    
    # 3. PIPELINE STEPS
    logger.info("3️⃣  PIPELINE STEPS")
    
    today = get_today()
    from .database import get_pipeline_state, get_last_successful_run
    state = get_pipeline_state(today)
    
    # Get last successful run date
    last_run_date = get_last_successful_run()
    
    # Make pipeline state more prominent
    if state['status'] == 'idle':
        if last_run_date:
            if last_run_date == today:
                logger.info(f"   Pipeline state: IDLE (completed earlier today)")
            else:
                logger.warning(f"   ⚠️  Pipeline state: IDLE - NO RUN TODAY")
                logger.warning(f"   ⚠️  Last successful run: {last_run_date}")
        else:
            logger.warning(f"   ⚠️  Pipeline state: IDLE - NEVER RUN")
    else:
        logger.info(f"   Pipeline state: {state['status'].upper()}")
        if last_run_date and last_run_date != today:
            logger.info(f"   Last successful run: {last_run_date}")
    
    logger.info("")
    
    # Define all steps with emojis and CLI commands
    all_steps = [
        ('sync-ftp', '📥 Sync FTP ticker lists', 'sync-ftp'),
        ('extract-prices', '💹 Extract price/volume data', 'extract-prices'),
        ('extract-metadata', '📊 Extract detailed metrics', 'extract-metadata'),
        ('build', '🔨 Calculate strategy scores', 'build'),
        ('generate-hugo', '📄 Generate Hugo content', 'hugo all')
    ]
    
    for step_name, step_desc, cli_command in all_steps:
        # Check if this step is in completed_steps
        if step_name in state['completed_steps']:
            # Get details from DB
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tickers_processed, completed_at
                FROM pipeline_steps
                WHERE step_name = ? AND run_date = ? AND status = 'completed'
            """, (step_name, today))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                count, timestamp = result
                logger.info(f"   ✓ {step_desc}: Completed ({count:,} items)")
        
        elif step_name == state['current_step']:
            # In progress
            if state['progress']:
                current, total = state['progress']
                pct = (current / total * 100) if total > 0 else 0
                logger.info(f"   🔄 {step_desc}: IN PROGRESS ({current:,}/{total:,}, {pct:.1f}%)")
            else:
                logger.info(f"   🔄 {step_desc}: IN PROGRESS")
        
        else:
            # Not started - show CLI command to run this step
            logger.info(f"   ⏸  {step_desc}: Not started (python -m stock_ticker.cli {cli_command})")
    
    logger.info("")
    
    # 4. ENHANCED RECOMMENDATION
    logger.info("4️⃣  RECOMMENDATION")
    
    # Check for missing dependencies first
    if missing_deps:
        logger.error("   ❌ Missing Python dependencies")
        logger.error(f"   → Install with: pip install -r requirements.txt")
        logger.error(f"   → Missing: {', '.join(missing_deps)}")
        sys.exit(2)  # Exit code 2: missing dependencies
    
    # Check for database issues
    if db_issue_reason:
        if db_issue_reason == "migrations_pending":
            logger.warning("   ⚠️  Database migrations pending")
            logger.info("   → Run migrations with: python -m stock_ticker.cli migrate up")
        elif db_issue_reason in ("schema_missing", "tables_incomplete"):
            logger.warning("   ⚠️  Database schema not initialized")
            logger.info("   → Initialize with: python -m stock_ticker.cli init")
        elif db_issue_reason == "connection_error":
            logger.warning("   ⚠️  Database connection error")
            logger.info("   → Check database file permissions and connectivity")
        sys.exit(3)  # Exit code 3: database not ready
    
    # Check for unreachable services
    if unreachable_services:
        logger.warning("   ⚠️  External services unreachable")
        logger.warning(f"   → Check network connectivity")
        logger.warning(f"   → Unreachable: {', '.join(unreachable_services)}")
        if not ftp_reachable:
            logger.warning(f"   → Test FTP: telnet {FTP_HOST} 21")
        if not yahoo_reachable:
            logger.warning(f"   → Test Yahoo: curl -I https://{YAHOO_API_HOST}")
        sys.exit(4)  # Exit code 4: external services unreachable
    
    # Now check pipeline state
    if state['status'] == 'idle':
        if last_run_date == today:
            logger.info("   ✓ Pipeline complete for today!")
            logger.info("   💡 Run again tomorrow for fresh data")
            sys.exit(0)  # Success
        else:
            logger.warning("   ⚠️  Pipeline has not run today")
            logger.info("   💡 Run full pipeline")
            logger.info("   → python -m stock_ticker.cli run-all")
            sys.exit(1)  # Exit code 1: needs to run
    
    elif state['status'] == 'in_progress':
        logger.info("   ⚠️  Pipeline interrupted - resume to continue")
        logger.info("   → python -m stock_ticker.cli run-all")
        sys.exit(5)  # Exit code 5: pipeline interrupted
    
    elif state['status'] == 'completed':
        logger.info("   ✓ Pipeline complete for today!")
        logger.info("   💡 Run again tomorrow for fresh data")
        sys.exit(0)  # Success
    
    elif state['status'] == 'failed':
        logger.error("   ❌ Pipeline failed - review logs and restart")
        logger.error("   → python -m stock_ticker.cli run-all")
        logger.error(f"   → Check logs: {ERROR_LOG_PATH}")
        sys.exit(6)  # Exit code 6: pipeline failed
    
    elif state['status'] == 'partial':
        logger.info("   ⚠️  Pipeline partially complete - continue")
        logger.info("   → python -m stock_ticker.cli run-all")
        sys.exit(7)  # Exit code 7: pipeline partial

@cli.command()
@click.pass_context
@log_timing
def init(ctx):
    """Initialize the database schema."""
    init_db(dry_run=ctx.obj.dry_run)


@cli.group()
def migrate():
    """Manage database schema migrations."""
    pass


@migrate.command('status')
def migrate_status_cmd():
    """Show migration status."""
    ensure_migrations_table()
    
    status = migration_status()
    
    logger.info("=" * 70)
    logger.info("=== 📋 DATABASE MIGRATION STATUS ===")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Total migrations: {status['total']}")
    logger.info(f"Applied: {status['applied']}")
    logger.info(f"Pending: {status['pending']}")
    logger.info("")
    
    if status['migrations']:
        logger.info("Migrations:")
        for m in status['migrations']:
            status_icon = "✓" if m['applied'] else "○"
            status_text = "APPLIED" if m['applied'] else "PENDING"
            logger.info(f"  {status_icon} {m['version']:03d}: {m['description']} - {status_text}")
    else:
        logger.info("No migration files found")
    
    logger.info("")
    
    if status['pending'] > 0:
        logger.warning("⚠️  Pending migrations detected!")
        logger.info("→ Apply with: python -m stock_ticker.cli migrate up")
        sys.exit(1)
    else:
        logger.info("✓ Database schema is up to date")
        sys.exit(0)


@migrate.command('up')
def migrate_up_cmd():
    """Apply all pending migrations."""
    logger.info("=" * 70)
    logger.info("=== 🔼 APPLYING MIGRATIONS ===")
    logger.info("=" * 70)
    logger.info("")
    
    try:
        migrate_up()
        logger.info("")
        logger.info("✓ All migrations applied successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        sys.exit(1)


@migrate.command('down')
@click.confirmation_option(prompt='Are you sure you want to rollback the last migration?')
def migrate_down_cmd():
    """Rollback the most recent migration."""
    logger.info("=" * 70)
    logger.info("=== 🔽 ROLLING BACK MIGRATION ===")
    logger.info("=" * 70)
    logger.info("")
    logger.warning("Note: SQLite doesn't support DROP COLUMN - this only removes migration records")
    logger.info("")
    
    try:
        migrate_down()
        logger.info("")
        logger.info("✓ Migration rolled back")
        sys.exit(0)
    except Exception as e:
        logger.error(f"✗ Rollback failed: {e}")
        sys.exit(1)


@cli.command('sync-ftp')
@click.option('--clean', is_flag=True, help='Clean today\'s data before running')
@click.pass_context
@log_timing
def sync_ftp_cmd(ctx, clean):
    """Download and parse ticker lists from NASDAQ FTP."""
    ensure_initialized()
    
    if clean:
        logger.info("")
        logger.info("🧹 Cleaning today's sync-ftp data...")
        clean_today_data(step_name='sync-ftp', dry_run=ctx.obj.dry_run)
        logger.info("")
    
    sync_ftp(dry_run=ctx.obj.dry_run)


@cli.command('extract-prices')
@click.option('--limit', type=int, default=None, help='Limit ticker processing for testing')
@click.option('--clean', is_flag=True, help='Clean today\'s data before running')
@click.pass_context
@log_timing
def extract_prices_cmd(ctx, limit, clean):
    """Pass 1: Fetch price/volume data for all tickers."""
    ensure_initialized()
    
    if clean:
        logger.info("")
        logger.info("🧹 Cleaning today's extract-prices data...")
        clean_today_data(step_name='extract-prices', dry_run=ctx.obj.dry_run)
        logger.info("")
    
    extract_prices(dry_run=ctx.obj.dry_run, limit=limit)


@cli.command('extract-metadata')
@click.option('--limit', type=int, default=None, help='Limit ticker processing for testing')
@click.option('--clean', is_flag=True, help='Clean today\'s data before running')
@click.pass_context
@log_timing
def extract_metadata_cmd(ctx, limit, clean):
    """Pass 2: Fetch detailed metrics for filtered tickers."""
    ensure_initialized()
    
    if clean:
        logger.info("")
        logger.info("🧹 Cleaning today's extract-metadata data...")
        clean_today_data(step_name='extract-metadata', dry_run=ctx.obj.dry_run)
        logger.info("")
    
    extract_metadata(dry_run=ctx.obj.dry_run, limit=limit)


@cli.command()
@click.option('--clean', is_flag=True, help='Clean today\'s data before running')
@click.pass_context
@log_timing
def build(ctx, clean):
    """Generate JSON assets (trie.json and metadata.json)."""
    ensure_initialized()
    
    if clean:
        logger.info("")
        logger.info("🧹 Cleaning today's build data...")
        clean_today_data(step_name='build', dry_run=ctx.obj.dry_run)
        logger.info("")
    
    build_assets(dry_run=ctx.obj.dry_run)


def print_pipeline_summary():
    """Print summary after running full pipeline."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("=== 📊 PIPELINE SUMMARY ===")
    logger.info("=" * 70)
    logger.info("")
    
    conn = get_connection()
    cursor = conn.cursor()
    today = get_today()
    
    # Get counts
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) 
        FROM daily_metrics 
        WHERE date = ? AND price IS NOT NULL
    """, (today,))
    price_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) 
        FROM daily_metrics 
        WHERE date = ? AND market_cap IS NOT NULL
    """, (today,))
    metadata_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) 
        FROM strategy_scores 
        WHERE date = ?
    """, (today,))
    score_count = cursor.fetchone()[0]
    
    conn.close()
    
    logger.info(f"📈 Tickers with price data: {price_count}")
    logger.info(f"📊 Tickers with metadata: {metadata_count}")
    logger.info(f"🎯 Tickers with strategy scores: {score_count}")
    logger.info("")
    
    # Check output files
    trie_path = API_DIR / "trie.json"
    metadata_path = API_DIR / "metadata.json"
    
    if trie_path.exists() and metadata_path.exists():
        logger.info("✅ Output files generated:")
        logger.info(f"   • trie.json ({trie_path.stat().st_size / 1024:.1f} KB)")
        logger.info(f"   • metadata.json ({metadata_path.stat().st_size / 1024:.1f} KB)")
    else:
        logger.warning("⚠️  Output files not generated (may need more data)")
    
    logger.info("")
    logger.info("=" * 70)


@cli.command('run-all')
@click.option('--limit', type=int, default=None, help='Limit ticker processing for testing (e.g., --limit 10)')
@click.option('--force', is_flag=True, help='Force re-run even if already completed today (does not reset state)')
@click.option('--clean', is_flag=True, help='Clean today\'s data before running (resets pipeline state)')
@click.pass_context
def run_all(ctx, limit, force, clean):
    """Execute all pipeline steps in sequence."""
    pipeline_start_time = time.time()
    step_timings = {}
    
    logger.info("=" * 70)
    logger.info("=== 🚀 RUNNING FULL DATA PIPELINE ===")
    logger.info("=" * 70)
    logger.info("")
    
    if limit:
        logger.info(f"⚠️  LIMIT MODE: Processing limited to {limit} tickers for testing")
    
    if force:
        logger.info(f"⚠️  FORCE MODE: Will ignore completion status")
    
    if clean:
        logger.info(f"🧹 CLEAN MODE: Resetting today's pipeline data...")
    
    if limit or force or clean:
        logger.info("")
    
    # Check pipeline state
    today = get_today()
    from .database import get_pipeline_state
    state = get_pipeline_state(today)
    
    logger.info(f"Pipeline state: {state['status'].upper()}")
    
    if state['status'] == 'in_progress':
        logger.info(f"⚠️  Found interrupted pipeline from today")
        logger.info(f"   Step: {state['current_step']}")
        if state['progress']:
            current, total = state['progress']
            pct = (current / total * 100) if total > 0 else 0
            logger.info(f"   Progress: {current:,}/{total:,} ({pct:.1f}%)")
        logger.info("")
        logger.info("🔄 Resuming from where we left off...")
        logger.info("")
    
    elif state['status'] == 'completed':
        if not force:
            logger.info("✓ Pipeline already completed for today")
            logger.info("")
            logger.info("Completed steps:")
            for step in state['completed_steps']:
                logger.info(f"  ✓ {step}")
            logger.info("")
            logger.info("💡 Run again tomorrow for fresh data, or use --force to override.")
            return
        else:
            logger.info("  (ignoring completed state due to --force flag)")
            logger.info("")
            # Clear completed steps when forcing a re-run
            state['completed_steps'] = []
    
    elif state['completed_steps']:
        logger.info(f"🔄 Resuming partial pipeline")
        logger.info(f"   Already completed: {', '.join(state['completed_steps'])}")
        logger.info("")
    
    if ctx.obj.dry_run:
        logger.info("DRY RUN: Full pipeline simulation")
        logger.info("")
        logger.info("Step 1: Initialize database (if needed)")
        logger.info("Step 2: Sync FTP (download NASDAQ ticker lists)")
        logger.info("Step 3: Extract prices (Pass 1 - price/volume)")
        logger.info("Step 4: Extract metadata (Pass 2 - detailed metrics)")
        logger.info("Step 5: Build (generate JSON assets)")
        logger.info("Step 6: Generate Hugo (create site content)")
        logger.info("")
        logger.info("DRY RUN: No actual changes would be made")
        return
    
    # Initialize if needed (automatic)
    ensure_initialized()
    
    # Clean today's data if --clean flag is set
    if clean and not ctx.obj.dry_run:
        logger.info("")
        logger.info("🧹 Cleaning all today's data...")
        clean_today_data(step_name=None, dry_run=False)
        logger.info("")
        # After cleaning, reset state to force fresh run
        state['completed_steps'] = []
        state['status'] = 'idle'
    
    # Check service reachability before starting
    from .utils import check_ftp_server, check_yahoo_finance
    nasdaq_ftp_reachable = check_ftp_server(FTP_HOST)
    yahoo_finance_reachable = check_yahoo_finance(YAHOO_API_HOST)
    
    # Create pipeline run record
    from .database import create_pipeline_run, update_pipeline_run
    run_id = create_pipeline_run(today, nasdaq_ftp_reachable, yahoo_finance_reachable)
    
    # Track success
    pipeline_failed = False
    failed_step = None
    
    try:
        # Sync FTP (skip if already done)
        if 'sync-ftp' not in state['completed_steps']:
            logger.info("")
            logger.info("📥 Step 1: Syncing FTP ticker lists...")
            step_start = time.time()
            sync_ftp(dry_run=False)
            step_timings['sync-ftp'] = time.time() - step_start
        else:
            logger.info("")
            logger.info("📥 Step 1: Syncing FTP ticker lists... ✓ Already completed")
        
        # Extract prices (skip if already done)
        if 'extract-prices' not in state['completed_steps']:
            logger.info("")
            logger.info("💹 Step 2: Extracting price/volume data (Pass 1)...")
            step_start = time.time()
            extract_prices(dry_run=False, limit=limit, run_id=run_id)
            step_timings['extract-prices'] = time.time() - step_start
        else:
            logger.info("")
            logger.info("💹 Step 2: Extracting price/volume data (Pass 1)... ✓ Already completed")
        
        # Extract metadata (skip if already done)
        if 'extract-metadata' not in state['completed_steps']:
            logger.info("")
            logger.info("📊 Step 3: Extracting detailed metrics (Pass 2)...")
            step_start = time.time()
            extract_metadata(dry_run=False, limit=limit, run_id=run_id)
            step_timings['extract-metadata'] = time.time() - step_start
        else:
            logger.info("")
            logger.info("📊 Step 3: Extracting detailed metrics (Pass 2)... ✓ Already completed")
        
        # Build assets (skip if already done)
        if 'build' not in state['completed_steps']:
            logger.info("")
            logger.info("🔨 Step 4: Calculating strategy scores & building JSON...")
            step_start = time.time()
            build_assets(dry_run=False)
            step_timings['build'] = time.time() - step_start
        else:
            logger.info("")
            logger.info("🔨 Step 4: Calculating strategy scores & building JSON... ✓ Already completed")
        
        # Generate Hugo content (NEW STEP)
        if 'generate-hugo' not in state['completed_steps']:
            logger.info("")
            logger.info("📄 Step 5: Generating Hugo site content...")
            step_start = time.time()
            generate_all_hugo_content(dry_run=False)
            step_timings['generate-hugo'] = time.time() - step_start
        else:
            logger.info("")
            logger.info("📄 Step 5: Generating Hugo site content... ✓ Already completed")
        
    except Exception as e:
        pipeline_failed = True
        failed_step = "unknown"
        
        # Determine which step failed based on traceback or context
        import traceback
        tb = traceback.format_exc()
        if 'sync_ftp' in tb:
            failed_step = "sync-ftp"
        elif 'extract_prices' in tb:
            failed_step = "extract-prices"
        elif 'extract_metadata' in tb:
            failed_step = "extract-metadata"
        elif 'build_assets' in tb:
            failed_step = "build"
        
        logger.error("")
        logger.error("=" * 70)
        logger.error("=== ❌ PIPELINE FAILED ===")
        logger.error("=" * 70)
        logger.error(f"❌ Failed at step: {failed_step}")
        logger.error(f"❌ Error: {e}")
        logger.error("")
        logger.error(f"Check error log: {ERROR_LOG_PATH}")
        logger.error("=" * 70)
        
        # Record failure in pipeline steps
        from .database import record_pipeline_step
        record_pipeline_step(failed_step, 0, 'failed', dry_run=False)
        
        # Update pipeline run with failure
        update_pipeline_run(
            run_id,
            status='failed',
            failed_step=failed_step,
            timings={'total': time.time() - pipeline_start_time}
        )
        
        # Re-raise to ensure non-zero exit code
        raise
    
    # Summary
    if not pipeline_failed:
        print_pipeline_summary()
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("=== ✅ PIPELINE COMPLETE ===")
        logger.info("=" * 70)
        
        # Print timing breakdown
        total_elapsed = time.time() - pipeline_start_time
        if step_timings:
            logger.info("")
            logger.info("⏱️  Timing Breakdown:")
            for step_name, duration in step_timings.items():
                logger.info(f"   • {step_name}: {format_duration(duration)}")
            logger.info(f"   • TOTAL: {format_duration(total_elapsed)}")
        
        # Print request metrics summary
        metrics = get_request_metrics()
        logger.info("")
        logger.info(metrics.summary())
        
        # Get ticker counts from database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = ? AND price IS NOT NULL", (today,))
        tickers_with_prices = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = ? AND market_cap IS NOT NULL", (today,))
        tickers_with_metadata = cursor.fetchone()[0]
        conn.close()
        
        # Update pipeline run with success
        update_pipeline_run(
            run_id,
            status='completed',
            metrics={
                'total_requests': metrics.get_total(),
                'total_failures': metrics.get_total_failures(),
                'total_bytes_downloaded': metrics.get_total_bytes(),
                'tickers_processed_prices': tickers_with_prices,
                'tickers_processed_metadata': tickers_with_metadata
            },
            timings={
                'sync_ftp': step_timings.get('sync-ftp'),
                'extract_prices': step_timings.get('extract-prices'),
                'extract_metadata': step_timings.get('extract-metadata'),
                'build': step_timings.get('build'),
                'generate_hugo': step_timings.get('generate-hugo'),
                'total': total_elapsed
            }
        )


@cli.command()
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def reset(ctx, force):
    """Reset today's data (with confirmation)."""
    logger.info("=" * 70)
    logger.info("=== ⚠️  RESET TODAY'S DATA ===")
    logger.info("=" * 70)
    
    if not DB_PATH.exists():
        logger.info("No database found. Nothing to reset.")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    today = get_today()
    
    # Check what data exists for today
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) FROM daily_metrics WHERE date = ?
    """, (today,))
    daily_metrics_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) FROM strategy_scores WHERE date = ?
    """, (today,))
    scores_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM pipeline_steps WHERE run_date = ?
    """, (today,))
    steps_count = cursor.fetchone()[0]
    
    # Check if there's anything to reset
    if daily_metrics_count == 0 and scores_count == 0 and steps_count == 0:
        if not force:
            logger.info("✓ No data found for today. Nothing to reset.")
            logger.info("   Use --force to reset anyway.")
            conn.close()
            return
        else:
            logger.info("⚠ No data found for today, but --force specified. Proceeding...")
    
    # Show what will be deleted
    logger.info("")
    logger.info(f"The following data for today ({today}) will be DELETED:")
    logger.info("")
    
    if ftp_synced:
        logger.warning(f"  ⚠ FTP Sync History: 1 record")
    else:
        logger.info(f"  • FTP Sync History: 0 records (none to delete)")
    
    if daily_metrics_count > 0:
        logger.warning(f"  ⚠ Daily Metrics: {daily_metrics_count} tickers")
    else:
        logger.info(f"  • Daily Metrics: 0 records (none to delete)")
    
    if scores_count > 0:
        logger.warning(f"  ⚠ Strategy Scores: {scores_count} tickers")
    else:
        logger.info(f"  • Strategy Scores: 0 records (none to delete)")
    
    if steps_count > 0:
        logger.warning(f"  ⚠ Pipeline Steps: {steps_count} step records")
    else:
        logger.info(f"  • Pipeline Steps: 0 records (none to delete)")
    
    # Check for output files
    trie_path = API_DIR / "trie.json"
    metadata_path = API_DIR / "metadata.json"
    
    if trie_path.exists() or metadata_path.exists():
        logger.warning("  ⚠ Output files may contain today's data (not automatically deleted)")
    
    logger.info("")
    
    # Confirmation
    if not force and not ctx.obj.dry_run:
        if not click.confirm("⚠️  Are you sure you want to delete this data?"):
            logger.info("Reset cancelled.")
            conn.close()
            return
    
    if ctx.obj.dry_run:
        logger.info("DRY RUN: Would delete all data for today")
        conn.close()
        return
    
    # Perform reset
    logger.info("Deleting data...")
    
    cursor.execute("DELETE FROM daily_metrics WHERE date = ?", (today,))
    cursor.execute("DELETE FROM strategy_scores WHERE date = ?", (today,))
    cursor.execute("DELETE FROM pipeline_steps WHERE run_date = ?", (today,))
    
    conn.commit()
    conn.close()
    
    logger.info("✓ Data reset complete.")
    logger.info(f"   You can now run 'ticker-cli run-all' to start fresh.")


@cli.group()
def hugo():
    """Generate content for Hugo static site."""
    pass


@hugo.command('raw-ftp')
@click.pass_context
def hugo_raw_ftp(ctx):
    """Generate raw FTP data (before filtering) for Hugo site."""
    generate_raw_ftp_data(dry_run=ctx.obj.dry_run)


@hugo.command('filtered')
@click.pass_context
def hugo_filtered(ctx):
    """Generate filtered ticker data (after Pass 1) for Hugo site."""
    generate_filtered_data(dry_run=ctx.obj.dry_run)


@hugo.command('strategies')
@click.pass_context
def hugo_strategies(ctx):
    """Generate strategy filter data for Hugo site."""
    generate_strategy_filters(dry_run=ctx.obj.dry_run)


@hugo.command('pages')
@click.pass_context
def hugo_pages(ctx):
    """Generate Hugo markdown pages."""
    generate_hugo_pages(dry_run=ctx.obj.dry_run)


@hugo.command('all-tickers')
@click.pass_context
def hugo_all_tickers(ctx):
    """Generate all_tickers.json for individual ticker detail pages."""
    generate_all_tickers_json(dry_run=ctx.obj.dry_run)


@hugo.command('all')
@click.option('--clean', is_flag=True, help='Clean today\'s data before running')
@click.pass_context
def hugo_all(ctx, clean):
    """Generate all Hugo site content."""
    if clean:
        logger.info("")
        logger.info("🧹 Cleaning today's generate-hugo data...")
        clean_today_data(step_name='generate-hugo', dry_run=ctx.obj.dry_run)
        logger.info("")
    
    generate_all_hugo_content(dry_run=ctx.obj.dry_run)


@cli.command()
@click.option("--path", default=None, help="Translate a single file instead of the full inventory.")
@click.option("--language", "languages", multiple=True, default=["zh-cn"], show_default=True,
              help="Target language code. Repeatable (e.g. --language zh-cn --language ko).")
@click.option("--workers", type=int, default=None,
              help="Parallel translation workers. Default: max(1, floor(cpu_count × 0.75)).")
@click.option("--utilization", type=float, default=None,
              help="CPU utilization fraction (0.0–1.0). Computes workers automatically. Mutually exclusive with --workers.")
@click.option("--timeout-per-file", type=int, default=300, show_default=True,
              help="Seconds to wait for a single file before marking it failed.")
@click.option("--retry", type=int, default=1, show_default=True,
              help="Number of retries on per-file failure.")
@click.option("--model", default="qwen2.5:7b", show_default=True,
              help="Ollama model to use.")
@click.option("--backend", type=click.Choice(["ollama", "huggingface"]), default="ollama", show_default=True,
              help="Translation backend.")
@click.option("--force", is_flag=True,
              help="Re-translate files that already have content.")
@click.option("--dry-run", is_flag=True,
              help="Print what would be translated; do not write files.")
@click.option("--no-heuristics", is_flag=True,
              help="Skip ETA estimate (useful for first run with no history).")
def translate(path, languages, workers, utilization, timeout_per_file, retry,
              model, backend, force, dry_run, no_heuristics):
    """Translate English content files to Simplified Chinese (or other languages).

    Walks hugo/site/content/ for English .md files without translated siblings,
    then runs Ollama translations in parallel with SQLite-backed ETA heuristics.
    """
    if workers is not None and utilization is not None:
        raise click.UsageError("--workers and --utilization are mutually exclusive.")
    if utilization is not None and not (0.0 < utilization <= 1.0):
        click.echo("Warning: --utilization clamped to 1.0", err=True)
        utilization = 1.0

    config = TranslateConfig(
        path=path,
        languages=list(languages),
        workers=workers,
        utilization=utilization,
        timeout_per_file=timeout_per_file,
        retry=retry,
        model=model,
        backend=backend,
        force=force,
        dry_run=dry_run,
        no_heuristics=no_heuristics,
    )
    run_translate(config)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
