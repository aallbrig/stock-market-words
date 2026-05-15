"""
Data extraction functions for price/volume and metadata.
"""
import math
import time
import yfinance as yf
import numpy as np
import pandas as pd
from .config import PRICE_BATCH_SIZE, METADATA_BATCH_SIZE, YAHOO_API_HOST
from .utils import get_today
from .database import get_connection, record_pipeline_step
from .logging_setup import setup_logging
from .retry import get_retry_tracker, get_request_metrics, BackoffLimitExceeded
from .vpn_rotator import get_vpn_rotator
from .download_strategies import DownloadStrategy, BatchDownloadStrategy, DownloadAborted

logger = setup_logging()


def extract_prices(dry_run=False, limit=None, run_id=None, strategy: DownloadStrategy = None):
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

    if strategy is None:
        strategy = BatchDownloadStrategy()

    processed = 0
    metrics = get_request_metrics()

    if run_id:
        from .database import batch_create_ticker_sync_records, batch_update_ticker_sync_records

    for i in range(0, total, PRICE_BATCH_SIZE):
        batch = pending_symbols[i:i + PRICE_BATCH_SIZE]
        batch_num = i // PRICE_BATCH_SIZE + 1
        total_batches = (total + PRICE_BATCH_SIZE - 1) // PRICE_BATCH_SIZE

        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} tickers)...")

        if run_id:
            batch_create_ticker_sync_records(run_id, 'price', batch, batch_num)

        successful_symbols = []
        failed_symbols = {}

        try:
            data = strategy.fetch_price_batch(batch)

            batch_data = []
            for symbol in batch:
                try:
                    ticker_data = data if len(batch) == 1 else (data[symbol] if symbol in data else None)
                    if ticker_data is not None and not ticker_data.empty:
                        row = ticker_data.iloc[-1]
                        def _float(col):
                            try: return float(row[col])
                            except Exception: return None
                        close_price = _float('Close')
                        if close_price is None:
                            failed_symbols[symbol] = "No Close price"
                            continue
                        batch_data.append((
                            symbol, today,
                            close_price,
                            int(row['Volume']) if row['Volume'] is not None else None,
                            _float('Open'),
                            _float('High'),
                            _float('Low'),
                            _float('Adj Close'),
                        ))
                        successful_symbols.append(symbol)
                    else:
                        failed_symbols[symbol] = "No price data returned"
                except Exception as e:
                    logger.debug(f"Failed to process {symbol}: {e}")
                    failed_symbols[symbol] = str(e)

            estimated_bytes = len(successful_symbols) * 200
            metrics.record_request('yahoo_finance', 'batch_download', bytes_downloaded=estimated_bytes)
            if failed_symbols:
                for _ in failed_symbols:
                    metrics.record_request('yahoo_finance', 'batch_download', failed=True)

            if run_id:
                batch_update_ticker_sync_records(run_id, 'price', batch_num, successful_symbols, failed_symbols)

            if batch_data:
                cursor.executemany("""
                    INSERT OR REPLACE INTO daily_metrics
                        (symbol, date, price, volume, open_price, high_price, low_price, adj_close)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, batch_data)
                conn.commit()
                processed += len(batch_data)
                logger.info(f"✓ Saved {len(batch_data)} tickers. Total: {processed:,}/{total:,}")
                if batch_num % 5 == 0:
                    record_pipeline_step('extract-prices', processed, 'in_progress', dry_run=False)
            else:
                logger.warning(f"Batch {batch_num} returned no data - possible Yahoo Finance API issue")

        except DownloadAborted as e:
            logger.error(f"CRITICAL: {e}")
            logger.error(f"Processed {processed:,} of {total:,} tickers before download was aborted")
            logger.error("Pipeline is idempotent — re-run 'run-all' later to resume from this point")
            if run_id:
                remaining = [s for s in batch if s not in successful_symbols]
                failed_symbols.update({s: "Download aborted" for s in remaining})
                batch_update_ticker_sync_records(run_id, 'price', batch_num, successful_symbols, failed_symbols)
            conn.close()
            raise

        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            metrics.record_request('yahoo_finance', 'batch_download', failed=True)
            if run_id:
                remaining = [s for s in batch if s not in successful_symbols]
                failed_symbols.update({s: str(e) for s in remaining})
                batch_update_ticker_sync_records(run_id, 'price', batch_num, successful_symbols, failed_symbols)

        if i + PRICE_BATCH_SIZE < total:
            strategy.inter_batch_pause()

    conn.close()
    logger.info(f"=== Pass 1 Complete: {processed:,} tickers processed ===")
    record_pipeline_step('extract-prices', processed, 'completed', dry_run=False)


def extract_metadata(dry_run=False, limit=None, run_id=None, strategy: DownloadStrategy = None):
    """Pass 2: Fetch deep metrics for filtered 'surviving' tickers."""
    if dry_run:
        logger.info("DRY RUN: Would extract metadata (Pass 2)")
        conn = get_connection()
        cursor = conn.cursor()
        today = get_today()
        cursor.execute("""
            SELECT COUNT(*) FROM daily_metrics
            WHERE date = ?
            AND (price >= 5.0 OR volume >= 10000000)
            AND volume >= 100000
            AND market_cap IS NULL
        """, (today,))
        pending = cursor.fetchone()[0]
        if limit:
            pending = min(pending, limit)
        conn.close()
        logger.info(f"DRY RUN: Would fetch metadata for {pending} filtered tickers")
        logger.info("DRY RUN: Would collect: market cap, dividend yield, beta, RSI, MA200")
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
    
    # Get tickers that passed the filter (price >= $5 or high-volume, min 100k volume)
    cursor.execute("""
        SELECT symbol FROM daily_metrics
        WHERE date = ?
        AND (price >= 5.0 OR volume >= 10000000)
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

    if strategy is None:
        strategy = BatchDownloadStrategy()

    processed = 0
    metrics = get_request_metrics()

    if run_id:
        from .database import batch_create_ticker_sync_records, batch_update_ticker_sync_records

    for i in range(0, total, METADATA_BATCH_SIZE):
        batch = pending_symbols[i:i + METADATA_BATCH_SIZE]
        batch_num = i // METADATA_BATCH_SIZE + 1
        total_batches = (total + METADATA_BATCH_SIZE - 1) // METADATA_BATCH_SIZE
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} tickers)...")

        if run_id:
            batch_create_ticker_sync_records(run_id, 'metadata', batch, batch_num)

        successful_symbols = []
        failed_symbols = {}
        batch_bytes = 0

        for symbol in batch:
            try:
                info = strategy.fetch_ticker_info(symbol)
                hist = strategy.fetch_ticker_history(symbol, period='1y')

                symbol_bytes = 7000
                batch_bytes += symbol_bytes

                # ── Existing fields ──────────────────────────────────────────
                market_cap = info.get('marketCap')
                dividend_yield = info.get('dividendYield')
                beta = info.get('beta')
                sector = info.get('sector')
                industry = info.get('industry')
                business_summary = info.get('longBusinessSummary')
                pe_ratio = info.get('trailingPE')
                forward_pe = info.get('forwardPE')
                price_to_book = info.get('priceToBook')
                peg_ratio = info.get('pegRatio')
                enterprise_value = info.get('enterpriseValue')
                week_52_high = info.get('fiftyTwoWeekHigh')
                week_52_low = info.get('fiftyTwoWeekLow')
                avg_volume_10day = info.get('averageVolume10days')
                short_ratio = info.get('shortRatio')
                short_percent_float = info.get('shortPercentOfFloat')
                debt_to_equity = info.get('debtToEquity')
                current_ratio = info.get('currentRatio')
                quick_ratio = info.get('quickRatio')
                profit_margin = info.get('profitMargins')
                operating_margin = info.get('operatingMargins')
                return_on_equity = info.get('returnOnEquity')
                return_on_assets = info.get('returnOnAssets')
                revenue_growth = info.get('revenueGrowth')
                earnings_growth = info.get('earningsGrowth')
                target_mean_price = info.get('targetMeanPrice')
                recommendation_mean = info.get('recommendationMean')
                num_analyst_opinions = info.get('numberOfAnalystOpinions')
                shares_outstanding = info.get('sharesOutstanding')
                float_shares = info.get('floatShares')

                # ── New fields: per-share and valuation ───────────────────────
                trailing_eps = info.get('trailingEps')
                forward_eps = info.get('forwardEps')
                book_value = info.get('bookValue')
                price_to_sales = info.get('priceToSalesTrailing12Months')

                # ── New fields: absolute income statement (TTM) ───────────────
                total_revenue = info.get('totalRevenue')
                gross_profit = info.get('grossProfits')
                ebitda = info.get('ebitda')
                operating_cashflow = info.get('operatingCashflow')
                free_cashflow = info.get('freeCashflow')

                # ── New fields: balance sheet ─────────────────────────────────
                total_cash = info.get('totalCash')
                total_debt = info.get('totalDebt')

                # ── New fields: margin stack ──────────────────────────────────
                gross_margins = info.get('grossMargins')
                ebitda_margins = info.get('ebitdaMargins')

                # ── New fields: ownership ─────────────────────────────────────
                held_percent_insiders = info.get('heldPercentInsiders')
                held_percent_institutions = info.get('heldPercentInstitutions')

                # ── New fields: dividend detail ───────────────────────────────
                dividend_rate = info.get('dividendRate')
                payout_ratio = info.get('payoutRatio')
                five_year_avg_dividend_yield = info.get('fiveYearAvgDividendYield')

                # ── New fields: short interest and momentum ───────────────────
                shares_short = info.get('sharesShort')
                week_52_change = info.get('52WeekChange')

                # ── New fields: slowly-changing company attributes ────────────
                country = info.get('country')
                full_time_employees = info.get('fullTimeEmployees')

                # ── Computed from history ─────────────────────────────────────
                ma_200 = hist['Close'].tail(200).mean() if not hist.empty and len(hist) >= 200 else None
                ma_50 = hist['Close'].tail(50).mean() if not hist.empty and len(hist) >= 50 else None

                rsi_14 = None
                if not hist.empty and len(hist) >= 14:
                    delta = hist['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    last_rs = rs.iloc[-1]
                    rsi_14 = float(100 - (100 / (1 + last_rs))) if not pd.isna(last_rs) else None

                hist_volatility = None
                if not hist.empty and len(hist) >= 21:
                    closes = hist['Close'].values.astype(float)
                    log_ret = np.log(closes[1:] / closes[:-1])
                    if len(log_ret) >= 20:
                        vol = float(np.std(log_ret[-20:], ddof=1) * math.sqrt(252) * 100)
                        hist_volatility = vol if not math.isnan(vol) else None

                atr_14 = None
                if not hist.empty and len(hist) >= 15:
                    h = pd.Series(hist['High'].values)
                    l = pd.Series(hist['Low'].values)
                    c = pd.Series(hist['Close'].values)
                    prev_c = c.shift(1)
                    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
                    last_atr = tr.rolling(14).mean().iloc[-1]
                    atr_14 = float(last_atr) if not pd.isna(last_atr) else None

                if sector or industry or business_summary or country or full_time_employees:
                    is_reit = 1 if (industry or '').startswith('REIT') else 0
                    cursor.execute("""
                        UPDATE tickers
                        SET sector = ?, industry = ?, is_reit = ?, business_summary = ?,
                            country = ?, full_time_employees = ?
                        WHERE symbol = ?
                    """, (sector, industry, is_reit, business_summary, country, full_time_employees, symbol))

                cursor.execute("""
                    UPDATE daily_metrics
                    SET market_cap = ?, dividend_yield = ?, beta = ?, rsi_14 = ?, ma_200 = ?,
                        pe_ratio = ?, forward_pe = ?, price_to_book = ?, peg_ratio = ?, enterprise_value = ?,
                        week_52_high = ?, week_52_low = ?, avg_volume_10day = ?,
                        short_ratio = ?, short_percent_float = ?,
                        debt_to_equity = ?, current_ratio = ?, quick_ratio = ?,
                        profit_margin = ?, operating_margin = ?, return_on_equity = ?, return_on_assets = ?,
                        revenue_growth = ?, earnings_growth = ?,
                        target_mean_price = ?, recommendation_mean = ?, num_analyst_opinions = ?,
                        ma_50 = ?, shares_outstanding = ?, float_shares = ?,
                        trailing_eps = ?, forward_eps = ?, book_value = ?, price_to_sales = ?,
                        total_revenue = ?, gross_profit = ?, ebitda = ?,
                        operating_cashflow = ?, free_cashflow = ?,
                        total_cash = ?, total_debt = ?,
                        gross_margins = ?, ebitda_margins = ?,
                        held_percent_insiders = ?, held_percent_institutions = ?,
                        dividend_rate = ?, payout_ratio = ?, five_year_avg_dividend_yield = ?,
                        shares_short = ?, week_52_change = ?,
                        hist_volatility = ?, atr_14 = ?
                    WHERE symbol = ? AND date = ?
                """, (
                    market_cap, dividend_yield, beta, rsi_14, ma_200,
                    pe_ratio, forward_pe, price_to_book, peg_ratio, enterprise_value,
                    week_52_high, week_52_low, avg_volume_10day,
                    short_ratio, short_percent_float,
                    debt_to_equity, current_ratio, quick_ratio,
                    profit_margin, operating_margin, return_on_equity, return_on_assets,
                    revenue_growth, earnings_growth,
                    target_mean_price, recommendation_mean, num_analyst_opinions,
                    ma_50, shares_outstanding, float_shares,
                    trailing_eps, forward_eps, book_value, price_to_sales,
                    total_revenue, gross_profit, ebitda,
                    operating_cashflow, free_cashflow,
                    total_cash, total_debt,
                    gross_margins, ebitda_margins,
                    held_percent_insiders, held_percent_institutions,
                    dividend_rate, payout_ratio, five_year_avg_dividend_yield,
                    shares_short, week_52_change,
                    hist_volatility, atr_14,
                    symbol, today
                ))

                conn.commit()
                processed += 1
                successful_symbols.append(symbol)
                metrics.record_request('yahoo_finance', 'ticker_info', bytes_downloaded=symbol_bytes)
                metrics.record_request('yahoo_finance', 'ticker_history', bytes_downloaded=0)

                if processed % 10 == 0:
                    logger.info(f"✓ Progress: {processed:,}/{total:,}")
                    record_pipeline_step('extract-metadata', processed, 'in_progress', dry_run=False)

            except DownloadAborted as e:
                logger.error(f"CRITICAL: {e}")
                logger.error(f"Processed {processed:,} of {total:,} tickers before download was aborted")
                logger.error("Pipeline is idempotent — re-run 'run-all' later to resume from this point")
                if run_id:
                    remaining = [s for s in batch if s not in successful_symbols]
                    failed_symbols.update({s: "Download aborted" for s in remaining})
                    batch_update_ticker_sync_records(run_id, 'metadata', batch_num, successful_symbols, failed_symbols)
                conn.close()
                raise

            except Exception as e:
                failed_symbols[symbol] = str(e)
                metrics.record_request('yahoo_finance', 'ticker_info', failed=True)
                metrics.record_request('yahoo_finance', 'ticker_history', failed=True)
                logger.debug(f"Failed to fetch metadata for {symbol}: {e}")

        if run_id:
            batch_update_ticker_sync_records(run_id, 'metadata', batch_num, successful_symbols, failed_symbols)

        if i + METADATA_BATCH_SIZE < total:
            strategy.inter_batch_pause()

    conn.close()
    logger.info(f"=== Pass 2 Complete: {processed:,} tickers processed ===")
    record_pipeline_step('extract-metadata', processed, 'completed', dry_run=False)
