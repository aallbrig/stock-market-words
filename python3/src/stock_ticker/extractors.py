"""
Data extraction functions for price/volume and metadata.
"""
import time
import yfinance as yf
import pandas as pd
from .config import PRICE_BATCH_SIZE, METADATA_BATCH_SIZE
from .utils import get_today
from .database import get_connection, record_pipeline_step
from .logging_setup import setup_logging

logger = setup_logging()


def extract_prices(dry_run=False):
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
        conn.close()
        logger.info(f"DRY RUN: Would fetch data for {pending} tickers")
        logger.info(f"DRY RUN: Would process in batches of {PRICE_BATCH_SIZE}")
        logger.info(f"DRY RUN: Estimated time: ~{pending * 1 / PRICE_BATCH_SIZE:.0f} minutes")
        return
    
    logger.info("=== Starting Pass 1: Price/Volume Extraction ===")
    
    conn = get_connection()
    cursor = conn.cursor()
    today = get_today()
    
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
    total = len(pending_symbols)
    
    if total == 0:
        # Show summary of already-completed work
        cursor.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = ? AND price IS NOT NULL", (today,))
        completed_count = cursor.fetchone()[0]
        
        logger.info("✓ All tickers already have price data for today.")
        logger.info(f"  • Tickers processed: {completed_count:,}")
        
        conn.close()
        return
    
    logger.info(f"Fetching price data for {total} tickers...")
    
    processed = 0
    
    for i in range(0, total, PRICE_BATCH_SIZE):
        batch = pending_symbols[i:i + PRICE_BATCH_SIZE]
        logger.info(f"Processing batch {i // PRICE_BATCH_SIZE + 1}/{(total + PRICE_BATCH_SIZE - 1) // PRICE_BATCH_SIZE} ({len(batch)} tickers)...")
        
        try:
            # Fetch data in batch
            tickers_str = ' '.join(batch)
            data = yf.download(tickers_str, period='1d', group_by='ticker', 
                               progress=False, threads=True)
            
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
                logger.info(f"✓ Saved {len(batch_data)} tickers. Total: {processed}/{total}")
            
            # Rate limiting
            if i + PRICE_BATCH_SIZE < total:
                time.sleep(1)
        
        except Exception as e:
            logger.error(f"Batch failed: {e}")
            continue
    
    conn.close()
    logger.info(f"=== Pass 1 Complete: {processed} tickers processed ===")
    
    # Record step completion
    record_pipeline_step('extract-prices', processed, 'completed', dry_run=False)


def extract_metadata(dry_run=False):
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
        conn.close()
        logger.info(f"DRY RUN: Would fetch metadata for {pending} filtered tickers")
        logger.info(f"DRY RUN: Would collect: market cap, dividend yield, beta, RSI, MA200")
        logger.info(f"DRY RUN: Estimated time: ~{pending * 1.5 / METADATA_BATCH_SIZE:.0f} minutes")
        return
    
    logger.info("=== Starting Pass 2: Metadata Extraction ===")
    
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
        
        conn.close()
        return
    
    logger.info(f"Fetching metadata for {total} filtered tickers...")
    
    processed = 0
    
    for i in range(0, total, METADATA_BATCH_SIZE):
        batch = pending_symbols[i:i + METADATA_BATCH_SIZE]
        logger.info(f"Processing batch {i // METADATA_BATCH_SIZE + 1}/{(total + METADATA_BATCH_SIZE - 1) // METADATA_BATCH_SIZE} ({len(batch)} tickers)...")
        
        for symbol in batch:
            try:
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
                
                if processed % 10 == 0:
                    logger.info(f"✓ Progress: {processed}/{total}")
            
            except Exception as e:
                logger.debug(f"Failed to fetch metadata for {symbol}: {e}")
                continue
        
        # Rate limiting
        if i + METADATA_BATCH_SIZE < total:
            time.sleep(1)
    
    conn.close()
    logger.info(f"=== Pass 2 Complete: {processed} tickers processed ===")
    
    # Record step completion
    record_pipeline_step('extract-metadata', processed, 'completed', dry_run=False)
