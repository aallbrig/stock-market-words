"""
Data extraction functions for price/volume and metadata.
"""
import time
import yfinance as yf
import pandas as pd
from .config import PRICE_BATCH_SIZE, METADATA_BATCH_SIZE, YAHOO_API_HOST
from .utils import get_today
from .database import get_connection, record_pipeline_step
from .logging_setup import setup_logging
from .retry import get_retry_tracker, get_request_metrics, BackoffLimitExceeded

logger = setup_logging()


def extract_prices(dry_run=False, limit=None):
    """Pass 1: Rapidly fetch price/volume for entire universe."""
    if dry_run:
        logger.info("DRY RUN: Would extract price/volume data (Pass 1)")
        conn = get_connection()
        cursor = conn.cursor()
        today = get_today()
        cursor.execute("""
            SELECT COUNT(*) FROM tickers 
            WHERE is_etf = 0
            AND symbol NOT IN (
                SELECT symbol FROM daily_metrics 
                WHERE date = ? AND price IS NOT NULL
            )
        """, (today,))
        pending = cursor.fetchone()[0]
        if limit:
            pending = min(pending, limit)
        conn.close()
        logger.info(f"DRY RUN: Would fetch data for {pending} tickers")
        logger.info(f"DRY RUN: Would process in batches of {PRICE_BATCH_SIZE}")
        logger.info(f"DRY RUN: Estimated time: ~{pending * 1 / PRICE_BATCH_SIZE:.0f} minutes")
        return
    
    logger.info("=== Starting Pass 1: Price/Volume Extraction ===")
    
    if limit:
        logger.info(f"⚠️  LIMIT MODE: Processing limited to {limit} tickers")
    
    conn = get_connection()
    cursor = conn.cursor()
    today = get_today()
    
    # Record step start
    record_pipeline_step('extract-prices', 0, 'in_progress', dry_run=False)
    
    # Get all valid tickers that need price data
    cursor.execute("""
        SELECT symbol FROM tickers 
        WHERE is_etf = 0
        AND symbol NOT IN (
            SELECT symbol FROM daily_metrics 
            WHERE date = ? AND price IS NOT NULL
        )
        ORDER BY symbol
    """, (today,))
    
    pending_symbols = [row[0] for row in cursor.fetchall()]
    
    # Apply limit if specified
    if limit:
        pending_symbols = pending_symbols[:limit]
    
    total = len(pending_symbols)
    
    if total == 0:
        # Show summary of already-completed work
        cursor.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = ? AND price IS NOT NULL", (today,))
        completed_count = cursor.fetchone()[0]
        
        logger.info("✓ All tickers already have price data for today.")
        logger.info(f"  • Tickers processed: {completed_count:,}")
        
        # Mark as completed
        record_pipeline_step('extract-prices', completed_count, 'completed', dry_run=False)
        conn.close()
        return
    
    logger.info(f"Fetching price data for {total:,} tickers...")
    
    processed = 0
    retry_tracker = get_retry_tracker()
    metrics = get_request_metrics()
    
    for i in range(0, total, PRICE_BATCH_SIZE):
        batch = pending_symbols[i:i + PRICE_BATCH_SIZE]
        batch_num = i // PRICE_BATCH_SIZE + 1
        total_batches = (total + PRICE_BATCH_SIZE - 1) // PRICE_BATCH_SIZE
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} tickers)...")
        
        try:
            # Record API request
            metrics.record_request('yahoo_finance', 'batch_download')
            
            # Fetch data in batch
            tickers_str = ' '.join(batch)
            data = yf.download(tickers_str, period='1d', group_by='ticker', 
                               progress=False, threads=True)
            
            # Success - reset backoff for this operation
            retry_tracker.record_success('yahoo_finance_batch')
            
            # Process results
            batch_data = []
            for symbol in batch:
                try:
                    if len(batch) == 1:
                        ticker_data = data
                    else:
                        ticker_data = data[symbol] if symbol in data else None
                    
                    if ticker_data is not None and not ticker_data.empty:
                        close_price = float(ticker_data['Close'].iloc[-1])
                        volume = int(ticker_data['Volume'].iloc[-1])
                        
                        batch_data.append((symbol, today, close_price, volume))
                
                except Exception as e:
                    logger.debug(f"Failed to process {symbol}: {e}")
                    continue
            
            # Insert batch into database
            if batch_data:
                cursor.executemany("""
                    INSERT OR REPLACE INTO daily_metrics (symbol, date, price, volume)
                    VALUES (?, ?, ?, ?)
                """, batch_data)
                conn.commit()
                processed += len(batch_data)
                logger.info(f"✓ Saved {len(batch_data)} tickers. Total: {processed:,}/{total:,}")
                
                # Update progress every 5 batches
                if batch_num % 5 == 0:
                    record_pipeline_step('extract-prices', processed, 'in_progress', dry_run=False)
            else:
                logger.warning(f"Batch {batch_num} returned no data - possible Yahoo Finance API issue")
            
            # Rate limiting
            if i + PRICE_BATCH_SIZE < total:
                time.sleep(1)
        
        except BackoffLimitExceeded as e:
            logger.error(f"CRITICAL: {e}")
            logger.error(f"Processed {processed:,} of {total:,} tickers before hitting rate limit threshold")
            logger.error("Pipeline is idempotent - re-run 'run-all' later to resume from this point")
            conn.close()
            raise
        
        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            error_msg = str(e).lower()
            
            if "rate limit" in error_msg or "429" in error_msg:
                logger.error("Yahoo Finance API rate limit detected")
                try:
                    retry_tracker.record_failure('yahoo_finance_batch')
                except BackoffLimitExceeded:
                    raise
            elif "connection" in error_msg or "timeout" in error_msg:
                logger.error(f"Network issue connecting to {YAHOO_API_HOST}")
                try:
                    retry_tracker.record_failure('yahoo_finance_batch')
                except BackoffLimitExceeded:
                    raise
            continue
    
    conn.close()
    logger.info(f"=== Pass 1 Complete: {processed:,} tickers processed ===")
    
    # Record step completion
    record_pipeline_step('extract-prices', processed, 'completed', dry_run=False)


def extract_metadata(dry_run=False, limit=None):
    """Pass 2: Fetch deep metrics for filtered 'surviving' tickers."""
    if dry_run:
        logger.info("DRY RUN: Would extract metadata (Pass 2)")
        conn = get_connection()
        cursor = conn.cursor()
        today = get_today()
        cursor.execute("""
            SELECT COUNT(*) FROM daily_metrics
            WHERE date = ?
            AND price >= 5.0
            AND volume >= 100000
            AND market_cap IS NULL
        """, (today,))
        pending = cursor.fetchone()[0]
        if limit:
            pending = min(pending, limit)
        conn.close()
        logger.info(f"DRY RUN: Would fetch metadata for {pending} filtered tickers")
        logger.info(f"DRY RUN: Would collect: market cap, dividend yield, beta, RSI, MA200")
        logger.info(f"DRY RUN: Estimated time: ~{pending * 1.5 / METADATA_BATCH_SIZE:.0f} minutes")
        return
    
    logger.info("=== Starting Pass 2: Detailed Metrics Extraction ===")
    if limit:
        logger.info(f"⚠️  LIMIT MODE: Processing limited to {limit} tickers")
    logger.info("")
    logger.info("Metrics to extract for each ticker:")
    logger.info("  • Market Cap - Company size/valuation")
    logger.info("  • Dividend Yield - Annual dividend as % of price")
    logger.info("  • Beta - Volatility measure (vs. market)")
    logger.info("  • RSI-14 - Momentum indicator (oversold/overbought)")
    logger.info("  • MA-200 - 200-day moving average (trend)")
    logger.info("")
    logger.info("These metrics enable strategy scoring in Step 4.")
    logger.info("")
    
    # Record step start
    record_pipeline_step('extract-metadata', 0, 'in_progress', dry_run=False)
    
    conn = get_connection()
    cursor = conn.cursor()
    today = get_today()
    
    # Get tickers that passed the filter (price >= $5, volume >= 100k)
    cursor.execute("""
        SELECT symbol FROM daily_metrics
        WHERE date = ?
        AND price >= 5.0
        AND volume >= 100000
        AND market_cap IS NULL
        ORDER BY symbol
    """, (today,))
    
    pending_symbols = [row[0] for row in cursor.fetchall()]
    
    # Apply limit if specified
    if limit:
        pending_symbols = pending_symbols[:limit]
    
    total = len(pending_symbols)
    
    if total == 0:
        # Show summary of already-completed work
        cursor.execute("""
            SELECT COUNT(*) FROM daily_metrics 
            WHERE date = ? 
            AND market_cap IS NOT NULL
        """, (today,))
        completed_count = cursor.fetchone()[0]
        
        logger.info("✓ All filtered tickers already have metadata for today.")
        logger.info(f"  • Tickers with complete metadata: {completed_count:,}")
        
        # Mark as completed
        record_pipeline_step('extract-metadata', completed_count, 'completed', dry_run=False)
        conn.close()
        return
    
    logger.info(f"Fetching data for {total:,} filtered tickers...")
    
    processed = 0
    retry_tracker = get_retry_tracker()
    metrics = get_request_metrics()
    
    for i in range(0, total, METADATA_BATCH_SIZE):
        batch = pending_symbols[i:i + METADATA_BATCH_SIZE]
        logger.info(f"Processing batch {i // METADATA_BATCH_SIZE + 1}/{(total + METADATA_BATCH_SIZE - 1) // METADATA_BATCH_SIZE} ({len(batch)} tickers)...")
        
        for symbol in batch:
            try:
                # Record API requests
                metrics.record_request('yahoo_finance', 'ticker_info')
                metrics.record_request('yahoo_finance', 'ticker_history')
                
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Extract metadata
                market_cap = info.get('marketCap')
                dividend_yield = info.get('dividendYield')
                beta = info.get('beta')
                
                # Calculate RSI and MA (simplified - would need historical data for real calc)
                hist = ticker.history(period='1y')
                if not hist.empty and len(hist) >= 200:
                    ma_200 = hist['Close'].tail(200).mean()
                else:
                    ma_200 = None
                
                # Simple RSI calculation (14-day)
                rsi_14 = None
                if not hist.empty and len(hist) >= 14:
                    delta = hist['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi_14 = float(100 - (100 / (1 + rs.iloc[-1]))) if not pd.isna(rs.iloc[-1]) else None
                
                # Update database
                cursor.execute("""
                    UPDATE daily_metrics
                    SET market_cap = ?, dividend_yield = ?, beta = ?, rsi_14 = ?, ma_200 = ?
                    WHERE symbol = ? AND date = ?
                """, (market_cap, dividend_yield, beta, rsi_14, ma_200, symbol, today))
                
                conn.commit()
                processed += 1
                
                # Success - reset backoff for this symbol
                retry_tracker.record_success(f'yahoo_finance_metadata:{symbol}')
                
                if processed % 10 == 0:
                    logger.info(f"✓ Progress: {processed:,}/{total:,}")
                    # Update pipeline_steps
                    record_pipeline_step('extract-metadata', processed, 'in_progress', dry_run=False)
            
            except BackoffLimitExceeded as e:
                logger.error(f"CRITICAL: {e}")
                logger.error(f"Processed {processed:,} of {total:,} tickers before hitting rate limit threshold")
                logger.error("Pipeline is idempotent - re-run 'run-all' later to resume from this point")
                conn.close()
                raise
            
            except Exception as e:
                error_msg = str(e).lower()
                if "rate limit" in error_msg or "429" in error_msg:
                    logger.error(f"Yahoo Finance API rate limit at {symbol}")
                    try:
                        retry_tracker.record_failure(f'yahoo_finance_metadata:{symbol}')
                    except BackoffLimitExceeded:
                        raise
                elif "connection" in error_msg or "timeout" in error_msg:
                    logger.warning(f"Network issue fetching {symbol}: {e}")
                    try:
                        retry_tracker.record_failure(f'yahoo_finance_metadata:{symbol}')
                    except BackoffLimitExceeded:
                        raise
                else:
                    logger.debug(f"Failed to fetch metadata for {symbol}: {e}")
                continue
        
        # Rate limiting
        if i + METADATA_BATCH_SIZE < total:
            time.sleep(1)
    
    conn.close()
    logger.info(f"=== Pass 2 Complete: {processed:,} tickers processed ===")
    
    # Record step completion
    record_pipeline_step('extract-metadata', processed, 'completed', dry_run=False)
