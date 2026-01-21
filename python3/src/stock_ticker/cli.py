"""
Click-based CLI for the stock ticker application.
"""
import sys
import click
from datetime import datetime, timezone
from pathlib import Path

from .logging_setup import setup_logging
from .config import DB_PATH, API_DIR, ERROR_LOG_PATH, FTP_HOST, YAHOO_API_HOST
from .database import (
    init_db, ensure_initialized, get_connection, 
    get_all_steps_today, get_last_pipeline_run, recommend_next_step
)
from .ftp_sync import sync_ftp
from .extractors import extract_prices, extract_metadata
from .builders import build_assets
from .hugo_generators import (
    generate_raw_ftp_data, 
    generate_filtered_data, 
    generate_strategy_filters,
    generate_hugo_pages,
    generate_all_hugo_content
)
from .utils import get_today, check_ftp_server, check_yahoo_finance

logger = setup_logging()


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
def status():
    """Check system readiness and pipeline status."""
    logger.info("=" * 70)
    logger.info("=== 📊 SYSTEM STATUS ===")
    logger.info("=" * 70)
    logger.info("")
    
    # Track various issues for exit code
    missing_deps = []
    unreachable_services = []
    db_issue = False
    
    # 1. DEPENDENCIES CHECK
    logger.info("1️⃣  DEPENDENCIES")
    
    # Database
    if not DB_PATH.exists():
        logger.warning("   ⚠ Database: NOT FOUND")
        db_issue = True
    else:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            if not tables:
                logger.warning("   ⚠ Database: Schema not initialized")
                db_issue = True
            else:
                logger.info("   ✓ Database: Ready")
        except Exception as e:
            logger.warning(f"   ⚠ Database: Error ({e})")
            db_issue = True
    
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
    
    # 2. PIPELINE STEPS
    logger.info("2️⃣  PIPELINE STEPS")
    
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
    
    # 3. ENHANCED RECOMMENDATION
    logger.info("3️⃣  RECOMMENDATION")
    
    # Check for missing dependencies first
    if missing_deps:
        logger.error("   ❌ Missing Python dependencies")
        logger.error(f"   → Install with: pip install -r requirements.txt")
        logger.error(f"   → Missing: {', '.join(missing_deps)}")
        sys.exit(2)  # Exit code 2: missing dependencies
    
    # Check for database issues
    if db_issue:
        logger.warning("   ⚠️  Database not initialized")
        logger.info("   → Initialize with: python -m stock_ticker.cli init")
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
def init(ctx):
    """Initialize the database schema."""
    init_db(dry_run=ctx.obj.dry_run)


@cli.command('sync-ftp')
@click.pass_context
def sync_ftp_cmd(ctx):
    """Download and parse ticker lists from NASDAQ FTP."""
    ensure_initialized()
    sync_ftp(dry_run=ctx.obj.dry_run)


@cli.command('extract-prices')
@click.pass_context
def extract_prices_cmd(ctx):
    """Pass 1: Fetch price/volume data for all tickers."""
    ensure_initialized()
    extract_prices(dry_run=ctx.obj.dry_run)


@cli.command('extract-metadata')
@click.pass_context
def extract_metadata_cmd(ctx):
    """Pass 2: Fetch detailed metrics for filtered tickers."""
    ensure_initialized()
    extract_metadata(dry_run=ctx.obj.dry_run)


@cli.command()
@click.pass_context
def build(ctx):
    """Generate JSON assets (trie.json and metadata.json)."""
    ensure_initialized()
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
@click.pass_context
def run_all(ctx):
    """Execute all pipeline steps in sequence."""
    logger.info("=" * 70)
    logger.info("=== 🚀 RUNNING FULL DATA PIPELINE ===")
    logger.info("=" * 70)
    
    # Check pipeline state
    today = get_today()
    from .database import get_pipeline_state
    state = get_pipeline_state(today)
    
    logger.info("")
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
        logger.info("✓ Pipeline already completed for today.")
        logger.info("")
        logger.info("Completed steps:")
        for step in state['completed_steps']:
            logger.info(f"  ✓ {step}")
        logger.info("")
        logger.info("💡 Run again tomorrow for fresh data.")
        return
    
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
    
    # Track success
    pipeline_failed = False
    failed_step = None
    
    try:
        # Sync FTP (skip if already done)
        if 'sync-ftp' not in state['completed_steps']:
            logger.info("")
            logger.info("📥 Step 1: Syncing FTP ticker lists...")
            sync_ftp(dry_run=False)
        else:
            logger.info("")
            logger.info("📥 Step 1: Syncing FTP ticker lists... ✓ Already completed")
        
        # Extract prices (skip if already done)
        if 'extract-prices' not in state['completed_steps']:
            logger.info("")
            logger.info("💹 Step 2: Extracting price/volume data (Pass 1)...")
            extract_prices(dry_run=False)
        else:
            logger.info("")
            logger.info("💹 Step 2: Extracting price/volume data (Pass 1)... ✓ Already completed")
        
        # Extract metadata (skip if already done)
        if 'extract-metadata' not in state['completed_steps']:
            logger.info("")
            logger.info("📊 Step 3: Extracting detailed metrics (Pass 2)...")
            extract_metadata(dry_run=False)
        else:
            logger.info("")
            logger.info("📊 Step 3: Extracting detailed metrics (Pass 2)... ✓ Already completed")
        
        # Build assets (skip if already done)
        if 'build' not in state['completed_steps']:
            logger.info("")
            logger.info("🔨 Step 4: Calculating strategy scores & building JSON...")
            build_assets(dry_run=False)
        else:
            logger.info("")
            logger.info("🔨 Step 4: Calculating strategy scores & building JSON... ✓ Already completed")
        
        # Generate Hugo content (NEW STEP)
        if 'generate-hugo' not in state['completed_steps']:
            logger.info("")
            logger.info("📄 Step 5: Generating Hugo site content...")
            generate_all_hugo_content(dry_run=False)
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
        
        # Re-raise to ensure non-zero exit code
        raise
    
    # Summary
    if not pipeline_failed:
        print_pipeline_summary()
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("=== ✅ PIPELINE COMPLETE ===")
        logger.info("=" * 70)


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
    
    cursor.execute("""
        SELECT sync_date FROM sync_history WHERE sync_date = ?
    """, (today,))
    ftp_synced = cursor.fetchone() is not None
    
    # Check if there's anything to reset
    if daily_metrics_count == 0 and scores_count == 0 and steps_count == 0 and not ftp_synced:
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
    cursor.execute("DELETE FROM sync_history WHERE sync_date = ?", (today,))
    
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


@hugo.command('all')
@click.pass_context
def hugo_all(ctx):
    """Generate all Hugo site content."""
    generate_all_hugo_content(dry_run=ctx.obj.dry_run)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
