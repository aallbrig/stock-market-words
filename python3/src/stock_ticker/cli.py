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
    
    # 1. DEPENDENCIES CHECK
    logger.info("1️⃣  DEPENDENCIES")
    all_deps_ok = True
    
    # Database
    if not DB_PATH.exists():
        logger.warning("   ⚠ Database: NOT FOUND")
        all_deps_ok = False
    else:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            if not tables:
                logger.warning("   ⚠ Database: Schema not initialized")
                all_deps_ok = False
            else:
                logger.info("   ✓ Database: Ready")
        except Exception as e:
            logger.warning(f"   ⚠ Database: Error ({e})")
            all_deps_ok = False
    
    # Python packages
    try:
        import yfinance
        logger.info(f"   ✓ yfinance: {yfinance.__version__}")
    except ImportError:
        logger.warning("   ⚠ yfinance: NOT INSTALLED")
        all_deps_ok = False
    
    try:
        import pandas as pd
        logger.info(f"   ✓ pandas: {pd.__version__}")
    except ImportError:
        logger.warning("   ⚠ pandas: NOT INSTALLED")
        all_deps_ok = False
    
    # External services
    if check_ftp_server(FTP_HOST):
        logger.info(f"   ✓ NASDAQ FTP: Reachable ({FTP_HOST})")
    else:
        logger.warning(f"   ⚠ NASDAQ FTP: Unreachable ({FTP_HOST})")
        all_deps_ok = False
    
    if check_yahoo_finance(YAHOO_API_HOST):
        logger.info(f"   ✓ Yahoo Finance API: Reachable ({YAHOO_API_HOST})")
    else:
        logger.warning(f"   ⚠ Yahoo Finance API: Unreachable ({YAHOO_API_HOST})")
        all_deps_ok = False
    
    logger.info("")
    
    # 2. PIPELINE STEPS
    logger.info("2️⃣  PIPELINE STEPS")
    
    if not DB_PATH.exists():
        logger.info("   No pipeline history (database not initialized)")
    else:
        conn = get_connection()
        cursor = conn.cursor()
        today = get_today()
        
        # Define the pipeline steps in order
        steps = [
            ('sync-ftp', '📥 Sync FTP ticker lists'),
            ('extract-prices', '💹 Extract price/volume data'),
            ('extract-metadata', '📊 Extract metadata'),
            ('build', '🔨 Build JSON assets')
        ]
        
        for step_name, step_label in steps:
            cursor.execute("""
                SELECT completed_at, tickers_processed 
                FROM pipeline_steps 
                WHERE step_name = ? AND run_date = ?
            """, (step_name, today))
            result = cursor.fetchone()
            
            if result:
                completed_at, tickers_processed = result
                logger.info(f"   ✓ {step_label}: Done ({tickers_processed} tickers)")
            else:
                # Check last run
                cursor.execute("""
                    SELECT run_date, completed_at 
                    FROM pipeline_steps 
                    WHERE step_name = ? 
                    ORDER BY run_date DESC, completed_at DESC 
                    LIMIT 1
                """, (step_name,))
                last_run = cursor.fetchone()
                if last_run:
                    logger.info(f"   ⏸  {step_label}: Last run {last_run[0]}")
                else:
                    logger.info(f"   ⏸  {step_label}: Never run")
        
        conn.close()
    
    logger.info("")
    
    # 3. RECOMMENDATION
    logger.info("3️⃣  RECOMMENDATION")
    
    if not all_deps_ok:
        logger.warning("   ⚠ Fix dependencies before running pipeline")
        logger.info("   → Check database, packages, and network connectivity")
    else:
        last_run = get_last_pipeline_run()
        if last_run:
            # Parse last run timestamp
            try:
                last_run_dt = datetime.fromisoformat(last_run.replace(' UTC', '+00:00'))
                now = datetime.now(timezone.utc)
                hours_since = (now - last_run_dt).total_seconds() / 3600
                
                if hours_since > 24:
                    logger.info(f"   💡 Run full pipeline (last run: {hours_since:.0f}h ago)")
                    logger.info("   → ticker-cli run-all")
                else:
                    next_step, reason = recommend_next_step()
                    if next_step:
                        logger.info(f"   💡 {reason}")
                        logger.info(f"   → ticker-cli {next_step}")
                    else:
                        logger.info("   ✓ Pipeline up to date")
            except Exception:
                logger.info("   💡 Run full pipeline")
                logger.info("   → ticker-cli run-all")
        else:
            logger.info("   💡 Run full pipeline (never run)")
            logger.info("   → ticker-cli run-all")
    
    logger.info("")
    logger.info("=" * 70)


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
    
    if ctx.obj.dry_run:
        logger.info("DRY RUN: Full pipeline simulation")
        logger.info("")
        logger.info("Step 1: Initialize database (if needed)")
        logger.info("Step 2: Sync FTP (download NASDAQ ticker lists)")
        logger.info("Step 3: Extract prices (Pass 1 - price/volume)")
        logger.info("Step 4: Extract metadata (Pass 2 - detailed metrics)")
        logger.info("Step 5: Build (generate JSON assets)")
        logger.info("")
        logger.info("DRY RUN: No actual changes would be made")
        return
    
    # Initialize if needed (automatic)
    ensure_initialized()
    
    # Track success
    pipeline_failed = False
    failed_step = None
    
    try:
        # Sync FTP
        logger.info("")
        logger.info("📥 Step 1: Syncing FTP ticker lists...")
        sync_ftp(dry_run=False)
        
        # Extract prices
        logger.info("")
        logger.info("💹 Step 2: Extracting price/volume data (Pass 1)...")
        extract_prices(dry_run=False)
        
        # Extract metadata
        logger.info("")
        logger.info("📊 Step 3: Extracting metadata (Pass 2)...")
        extract_metadata(dry_run=False)
        
        # Build assets
        logger.info("")
        logger.info("🔨 Step 4: Building JSON assets...")
        build_assets(dry_run=False)
        
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


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
