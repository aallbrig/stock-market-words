#!/usr/bin/env python3
"""
Stock Market Ticker Discovery CLI
Manages extraction, filtering, and processing of stock market data.
"""

import argparse
import sqlite3
import os
import sys
import time
import json
import socket
from datetime import date, datetime, timezone
from pathlib import Path
from ftplib import FTP
from typing import List, Dict, Tuple
import logging
import subprocess
import shutil

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    print("Error: Required packages not installed.")
    print("Please run: pip3 install yfinance pandas numpy")
    sys.exit(1)

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "market_data.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
TMP_DIR = BASE_DIR / "data" / "tmp"
API_DIR = BASE_DIR / "hugo" / "static" / "api"
ERROR_LOG_PATH = BASE_DIR / "data" / "error.log"

# Ensure directories exist
TMP_DIR.mkdir(parents=True, exist_ok=True)
API_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Configure logging with both console and file handlers
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(console_formatter)

# File handler for errors
file_handler = logging.FileHandler(ERROR_LOG_PATH)
file_handler.setLevel(logging.ERROR)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


def get_db_connection():
    """Create and return a database connection."""
    return sqlite3.connect(DB_PATH)


def get_today():
    """Return today's date as string."""
    return date.today().isoformat()


class TickerCLI:
    """Main CLI application class."""
    
    def __init__(self, dry_run=False):
        self.conn = None
        self.dry_run = dry_run
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
    
    def _record_step(self, step_name, tickers_processed=0, status='completed'):
        """Record that a pipeline step was completed."""
        if self.dry_run:
            return
        
        conn = self.connect_db()
        cursor = conn.cursor()
        today = get_today()
        
        cursor.execute("""
            INSERT OR REPLACE INTO pipeline_steps (step_name, run_date, completed_at, tickers_processed, status)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
        """, (step_name, today, tickers_processed, status))
        conn.commit()
    
    def _get_step_info(self, step_name):
        """Get information about when a step was last run."""
        if not DB_PATH.exists():
            return None
        
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            today = get_today()
            
            cursor.execute("""
                SELECT completed_at, tickers_processed, status
                FROM pipeline_steps
                WHERE step_name = ? AND run_date = ?
            """, (step_name, today))
            
            return cursor.fetchone()
        except Exception:
            return None
    
    def _get_all_steps_today(self):
        """Get all steps completed today."""
        if not DB_PATH.exists():
            return []
        
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            today = get_today()
            
            cursor.execute("""
                SELECT step_name, completed_at, tickers_processed, status
                FROM pipeline_steps
                WHERE run_date = ?
                ORDER BY completed_at
            """, (today,))
            
            return cursor.fetchall()
        except Exception:
            return []
    
    def _recommend_next_step(self):
        """Recommend the next step based on current progress."""
        if not DB_PATH.exists():
            return "run-all", "Database not initialized. Run './run.sh run-all' to start."
        
        conn = self.connect_db()
        cursor = conn.cursor()
        today = get_today()
        
        # Check if FTP sync is done
        cursor.execute("SELECT sync_date FROM sync_history WHERE sync_date = ?", (today,))
        if not cursor.fetchone():
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
            return "extract-prices", "Fetch price/volume data for all tickers (Pass 1)"
        elif price_count < total_tickers:
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
            return "extract-metadata", f"Fetch detailed metrics for {filtered_count} filtered tickers (Pass 2)"
        elif metadata_count < filtered_count:
            return "extract-metadata", f"Resume metadata extraction ({metadata_count}/{filtered_count} completed)"
        
        # Check if build is done
        cursor.execute("""
            SELECT COUNT(DISTINCT symbol) FROM strategy_scores WHERE date = ?
        """, (today,))
        score_count = cursor.fetchone()[0]
        
        if score_count == 0 and metadata_count > 0:
            return "build", f"Generate JSON assets from {metadata_count} tickers"
        
        # Everything is done
        return None, "✓ All steps completed for today!"
    
    def connect_db(self):
        """Establish database connection."""
        if self.conn is None:
            self.conn = get_db_connection()
        return self.conn
    
    def close_db(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _check_network_connectivity(self, host, port, timeout=5):
        """Check if a host is reachable."""
        try:
            socket.create_connection((host, port), timeout=timeout)
            return True
        except (socket.timeout, socket.error):
            return False
    
    def _check_ftp_server(self):
        """Check if NASDAQ FTP server is reachable."""
        try:
            ftp = FTP('ftp.nasdaqtrader.com', timeout=5)
            ftp.login()
            ftp.quit()
            return True
        except Exception:
            return False
    
    def _check_yahoo_finance(self):
        """Check if Yahoo Finance is reachable."""
        return self._check_network_connectivity('query1.finance.yahoo.com', 443, timeout=5)
    
    def _get_last_pipeline_run(self):
        """Get the timestamp of the last pipeline run."""
        if not DB_PATH.exists():
            return None
        
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(sync_timestamp) FROM sync_history
            """)
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
        except Exception:
            return None
    
    def cmd_status(self):
        """Check essential system readiness and pipeline status."""
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
                conn = self.connect_db()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
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
        if self._check_ftp_server():
            logger.info("   ✓ NASDAQ FTP: Reachable (ftp.nasdaqtrader.com)")
        else:
            logger.warning("   ⚠ NASDAQ FTP: Unreachable (ftp.nasdaqtrader.com)")
            all_deps_ok = False
        
        if self._check_yahoo_finance():
            logger.info("   ✓ Yahoo Finance API: Reachable (query1.finance.yahoo.com)")
        else:
            logger.warning("   ⚠ Yahoo Finance API: Unreachable (query1.finance.yahoo.com)")
            all_deps_ok = False
        
        logger.info("")
        
        # 2. PIPELINE STEPS
        logger.info("2️⃣  PIPELINE STEPS")
        
        if not DB_PATH.exists():
            logger.info("   No pipeline history (database not initialized)")
        else:
            conn = self.connect_db()
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
        
        logger.info("")
        
        # 3. RECOMMENDATION
        logger.info("3️⃣  RECOMMENDATION")
        
        if not all_deps_ok:
            logger.warning("   ⚠ Fix dependencies before running pipeline")
            logger.info("   → Check database, packages, and network connectivity")
        else:
            last_run = self._get_last_pipeline_run()
            if last_run:
                # Parse last run timestamp
                try:
                    last_run_dt = datetime.fromisoformat(last_run.replace(' UTC', '+00:00'))
                    now = datetime.now(timezone.utc)
                    hours_since = (now - last_run_dt).total_seconds() / 3600
                    
                    if hours_since > 24:
                        logger.info(f"   💡 Run full pipeline (last run: {hours_since:.0f}h ago)")
                        logger.info("   → ./run.sh run-all")
                    else:
                        next_step, reason = self._recommend_next_step()
                        if next_step:
                            logger.info(f"   💡 {reason}")
                            logger.info(f"   → ./run.sh {next_step}")
                        else:
                            logger.info("   ✓ Pipeline up to date")
                except Exception:
                    logger.info("   💡 Run full pipeline")
                    logger.info("   → ./run.sh run-all")
            else:
                logger.info("   💡 Run full pipeline (never run)")
                logger.info("   → ./run.sh run-all")
        
        logger.info("")
        logger.info("=" * 70)
    
    def _print_pipeline_summary(self):
        """Print summary after running full pipeline."""
        logger.info("")
        logger.info("=" * 70)
        logger.info("=== 📊 PIPELINE SUMMARY ===")
        logger.info("=" * 70)
        logger.info("")
        
        conn = self.connect_db()
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
    
    def cmd_init(self):
        """Initialize the database schema."""
        if self.dry_run:
            logger.info("DRY RUN: Would initialize database schema")
            logger.info(f"DRY RUN: Would create database at {DB_PATH}")
            logger.info("DRY RUN: Would execute schema.sql")
            return
        
        logger.info("Initializing database schema...")
        
        if not SCHEMA_PATH.exists():
            logger.error(f"Schema file not found: {SCHEMA_PATH}")
            sys.exit(1)
        
        with open(SCHEMA_PATH, 'r') as f:
            schema_sql = f.read()
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        # Execute schema (supports multiple statements)
        cursor.executescript(schema_sql)
        conn.commit()
        
        logger.info("✓ Database schema initialized successfully.")
    
    def _ensure_initialized(self):
        """Ensure database is initialized before running commands."""
        if not DB_PATH.exists():
            logger.info("Database not found. Initializing automatically...")
            self.cmd_init()
            return
        
        # Check if tables exist
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            logger.info("Database exists but is empty. Initializing schema...")
            self.cmd_init()
    
    def cmd_sync_ftp(self):
        """Download and parse ticker lists from NASDAQ FTP."""
        self._ensure_initialized()
        
        if self.dry_run:
            logger.info("DRY RUN: Would sync ticker lists from ftp.nasdaqtrader.com")
            logger.info("DRY RUN: Would download nasdaqlisted.txt")
            logger.info("DRY RUN: Would download otherlisted.txt")
            logger.info("DRY RUN: Would parse and insert tickers into database")
            return
        
        logger.info("Syncing ticker lists from ftp.nasdaqtrader.com...")
        
        conn = self.connect_db()
        cursor = conn.cursor()
        today = get_today()
        
        # Check if already synced today
        cursor.execute("SELECT sync_date FROM sync_history WHERE sync_date = ?", (today,))
        if cursor.fetchone():
            logger.info(f"✓ FTP already synced today ({today}). Skipping.")
            return
        
        tickers_added = 0
        
        # Download nasdaqlisted.txt
        nasdaq_file = TMP_DIR / "nasdaqlisted.txt"
        other_file = TMP_DIR / "otherlisted.txt"
        
        try:
            logger.info("Connecting to ftp.nasdaqtrader.com...")
            ftp = FTP('ftp.nasdaqtrader.com', timeout=30)
            ftp.login()
            ftp.cwd('SymbolDirectory')
            
            logger.info("Downloading nasdaqlisted.txt...")
            with open(nasdaq_file, 'wb') as f:
                ftp.retrbinary('RETR nasdaqlisted.txt', f.write)
            
            logger.info("Downloading otherlisted.txt...")
            with open(other_file, 'wb') as f:
                ftp.retrbinary('RETR otherlisted.txt', f.write)
            
            ftp.quit()
            logger.info("✓ Files downloaded successfully.")
        
        except Exception as e:
            logger.error(f"FTP download failed: {e}")
            sys.exit(1)
        
        # Parse nasdaqlisted.txt
        logger.info("Parsing nasdaqlisted.txt...")
        try:
            df_nasdaq = pd.read_csv(nasdaq_file, sep='|')
            df_nasdaq = df_nasdaq[df_nasdaq['Symbol'].notna()]
            df_nasdaq = df_nasdaq[:-1]  # Remove last row (file metadata)
            
            for _, row in df_nasdaq.iterrows():
                symbol = str(row['Symbol']).strip()
                name = str(row.get('Security Name', '')).strip()
                is_etf = row.get('ETF', 'N') == 'Y'
                
                # Filter out invalid symbols
                if self._is_valid_symbol(symbol):
                    cursor.execute("""
                        INSERT OR IGNORE INTO tickers (symbol, name, exchange, is_etf)
                        VALUES (?, ?, ?, ?)
                    """, (symbol, name, 'NASDAQ', is_etf))
                    if cursor.rowcount > 0:
                        tickers_added += 1
            
            logger.info(f"Processed {len(df_nasdaq)} NASDAQ tickers.")
        
        except Exception as e:
            logger.error(f"Failed to parse nasdaqlisted.txt: {e}")
        
        # Parse otherlisted.txt
        logger.info("Parsing otherlisted.txt...")
        try:
            df_other = pd.read_csv(other_file, sep='|')
            df_other = df_other[df_other['ACT Symbol'].notna()]
            df_other = df_other[:-1]  # Remove last row
            
            for _, row in df_other.iterrows():
                symbol = str(row['ACT Symbol']).strip()
                name = str(row.get('Security Name', '')).strip()
                exchange = str(row.get('Exchange', 'OTHER')).strip()
                is_etf = 'ETF' in name.upper()
                
                if self._is_valid_symbol(symbol):
                    cursor.execute("""
                        INSERT OR IGNORE INTO tickers (symbol, name, exchange, is_etf)
                        VALUES (?, ?, ?, ?)
                    """, (symbol, name, exchange, is_etf))
                    if cursor.rowcount > 0:
                        tickers_added += 1
            
            logger.info(f"Processed {len(df_other)} other exchange tickers.")
        
        except Exception as e:
            logger.error(f"Failed to parse otherlisted.txt: {e}")
        
        # Record sync
        cursor.execute("""
            INSERT OR REPLACE INTO sync_history (sync_date, tickers_synced)
            VALUES (?, ?)
        """, (today, tickers_added))
        
        conn.commit()
        logger.info(f"✓ FTP sync complete. {tickers_added} new tickers added.")
        
        # Record step completion
        self._record_step('sync-ftp', tickers_added, 'completed')
    
    def _is_valid_symbol(self, symbol: str) -> bool:
        """Check if symbol is valid (no warrants, preferred, test tickers)."""
        if not symbol or len(symbol) > 5:
            return False
        
        # Exclude symbols with special characters
        if '$' in symbol or '.' in symbol or '^' in symbol or '~' in symbol:
            return False
        
        # Exclude test tickers
        if symbol.endswith('TEST') or symbol.startswith('Z'):
            return False
        
        return True
    
    def cmd_extract_prices(self):
        """Pass 1: Rapidly fetch price/volume for entire universe."""
        self._ensure_initialized()
        
        if self.dry_run:
            logger.info("DRY RUN: Would extract price/volume data (Pass 1)")
            conn = self.connect_db()
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
            logger.info(f"DRY RUN: Would fetch data for {pending} tickers")
            logger.info(f"DRY RUN: Would process in batches of 100")
            logger.info(f"DRY RUN: Estimated time: ~{pending * 1 / 100:.0f} minutes")
            return
        
        logger.info("=== Starting Pass 1: Price/Volume Extraction ===")
        
        conn = self.connect_db()
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
            logger.info("✓ All tickers already have price data for today.")
            return
        
        logger.info(f"Fetching price data for {total} tickers...")
        
        batch_size = 100
        processed = 0
        
        for i in range(0, total, batch_size):
            batch = pending_symbols[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size} ({len(batch)} tickers)...")
            
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
                if i + batch_size < total:
                    time.sleep(1)
            
            except Exception as e:
                logger.error(f"Batch failed: {e}")
                continue
        
        logger.info(f"=== Pass 1 Complete: {processed} tickers processed ===")
        
        # Record step completion
        self._record_step('extract-prices', processed, 'completed')
    
    def cmd_extract_metadata(self):
        """Pass 2: Fetch deep metrics for filtered 'surviving' tickers."""
        self._ensure_initialized()
        
        if self.dry_run:
            logger.info("DRY RUN: Would extract metadata (Pass 2)")
            conn = self.connect_db()
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
            logger.info(f"DRY RUN: Would fetch metadata for {pending} filtered tickers")
            logger.info(f"DRY RUN: Would collect: market cap, dividend yield, beta, RSI, MA200")
            logger.info(f"DRY RUN: Estimated time: ~{pending * 1.5 / 50:.0f} minutes")
            return
        
        logger.info("=== Starting Pass 2: Metadata Extraction ===")
        
        conn = self.connect_db()
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
            logger.info("✓ All filtered tickers already have metadata for today.")
            return
        
        logger.info(f"Fetching metadata for {total} filtered tickers...")
        
        batch_size = 50  # Smaller batches for detailed data
        processed = 0
        
        for i in range(0, total, batch_size):
            batch = pending_symbols[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size} ({len(batch)} tickers)...")
            
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
            if i + batch_size < total:
                time.sleep(1)
        
        logger.info(f"=== Pass 2 Complete: {processed} tickers processed ===")
        
        # Record step completion
        self._record_step('extract-metadata', processed, 'completed')
    
    def cmd_build(self):
        """Generate optimized trie.json and metadata.json."""
        self._ensure_initialized()
        
        if self.dry_run:
            logger.info("DRY RUN: Would build JSON assets")
            conn = self.connect_db()
            today = get_today()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM daily_metrics 
                WHERE date = ? AND price >= 5.0 AND volume >= 100000 AND market_cap IS NOT NULL
            """, (today,))
            ticker_count = cursor.fetchone()[0]
            logger.info(f"DRY RUN: Would build from {ticker_count} tickers")
            logger.info(f"DRY RUN: Would calculate 5 strategy scores via percentile ranking")
            logger.info(f"DRY RUN: Would generate trie.json (autocomplete prefix tree)")
            logger.info(f"DRY RUN: Would generate metadata.json (full ticker data + scores)")
            logger.info(f"DRY RUN: Output directory: {API_DIR}")
            return
        
        logger.info("=== Starting Build Phase ===")
        
        conn = self.connect_db()
        today = get_today()
        
        # Load all tickers with complete data for today
        query = """
            SELECT 
                t.symbol, t.name, t.exchange,
                dm.price, dm.volume, dm.market_cap, 
                dm.dividend_yield, dm.beta, dm.rsi_14, dm.ma_200
            FROM tickers t
            JOIN daily_metrics dm ON t.symbol = dm.symbol
            WHERE dm.date = ?
            AND dm.price >= 5.0
            AND dm.volume >= 100000
            AND dm.market_cap IS NOT NULL
        """
        
        df = pd.read_sql_query(query, conn, params=(today,))
        
        if df.empty:
            logger.warning("No tickers found with complete data for today.")
            return
        
        logger.info(f"Building assets from {len(df)} tickers...")
        
        # Calculate strategy scores
        logger.info("Calculating strategy scores...")
        
        # Dividend Daddy: High yield + low volatility
        df['dividend_daddy_raw'] = (
            (df['dividend_yield'].fillna(0) * 100) + 
            (100 - df['beta'].fillna(1).abs() * 50)
        )
        
        # Moon Shot: High growth potential (high beta, oversold RSI)
        df['moon_shot_raw'] = (
            (df['beta'].fillna(0) * 50) + 
            (100 - df['rsi_14'].fillna(50))
        )
        
        # Falling Knife: Oversold + below MA
        df['falling_knife_raw'] = (
            (100 - df['rsi_14'].fillna(50)) + 
            ((df['ma_200'].fillna(df['price']) - df['price']) / df['price'] * 100)
        )
        
        # Over Hyped: Overbought (high RSI)
        df['over_hyped_raw'] = df['rsi_14'].fillna(50)
        
        # Institutional Whale: Large market cap
        df['inst_whale_raw'] = np.log10(df['market_cap'].fillna(1))
        
        # Convert to percentile ranks (1-100)
        score_columns = [
            'dividend_daddy_raw', 'moon_shot_raw', 'falling_knife_raw',
            'over_hyped_raw', 'inst_whale_raw'
        ]
        
        for col in score_columns:
            score_name = col.replace('_raw', '_score')
            df[score_name] = df[col].rank(pct=True) * 100
            df[score_name] = df[score_name].fillna(50).astype(int)
        
        # Save strategy scores to database
        cursor = conn.cursor()
        score_data = []
        
        for _, row in df.iterrows():
            score_data.append((
                row['symbol'], today,
                int(row['dividend_daddy_score']),
                int(row['moon_shot_score']),
                int(row['falling_knife_score']),
                int(row['over_hyped_score']),
                int(row['inst_whale_score'])
            ))
        
        cursor.executemany("""
            INSERT OR REPLACE INTO strategy_scores 
            (symbol, date, dividend_daddy_score, moon_shot_score, 
             falling_knife_score, over_hyped_score, inst_whale_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, score_data)
        conn.commit()
        
        logger.info("✓ Strategy scores saved to database.")
        
        # Build trie.json (prefix tree for autocomplete)
        logger.info("Building trie.json...")
        trie = {}
        
        for _, row in df.iterrows():
            symbol = row['symbol']
            name = row['name']
            
            # Add symbol to trie
            for i in range(1, len(symbol) + 1):
                prefix = symbol[:i].upper()
                if prefix not in trie:
                    trie[prefix] = []
                if symbol not in trie[prefix]:
                    trie[prefix].append(symbol)
            
            # Add name words to trie
            if pd.notna(name):
                words = name.upper().split()
                for word in words:
                    for i in range(1, min(len(word) + 1, 6)):  # Limit prefix length
                        prefix = word[:i]
                        if prefix not in trie:
                            trie[prefix] = []
                        if symbol not in trie[prefix]:
                            trie[prefix].append(symbol)
        
        trie_path = API_DIR / "trie.json"
        with open(trie_path, 'w') as f:
            json.dump(trie, f, separators=(',', ':'))
        
        logger.info(f"✓ trie.json saved ({len(trie)} prefixes)")
        
        # Build metadata.json
        logger.info("Building metadata.json...")
        metadata = {}
        
        for _, row in df.iterrows():
            symbol = row['symbol']
            metadata[symbol] = {
                'name': row['name'],
                'exchange': row['exchange'],
                'price': round(float(row['price']), 2),
                'volume': int(row['volume']),
                'marketCap': int(row['market_cap']) if pd.notna(row['market_cap']) else None,
                'dividendYield': round(float(row['dividend_yield'] * 100), 2) if pd.notna(row['dividend_yield']) else None,
                'beta': round(float(row['beta']), 2) if pd.notna(row['beta']) else None,
                'rsi': round(float(row['rsi_14']), 1) if pd.notna(row['rsi_14']) else None,
                'ma200': round(float(row['ma_200']), 2) if pd.notna(row['ma_200']) else None,
                'scores': {
                    'dividendDaddy': int(row['dividend_daddy_score']),
                    'moonShot': int(row['moon_shot_score']),
                    'fallingKnife': int(row['falling_knife_score']),
                    'overHyped': int(row['over_hyped_score']),
                    'instWhale': int(row['inst_whale_score'])
                }
            }
        
        metadata_path = API_DIR / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, separators=(',', ':'))
        
        logger.info(f"✓ metadata.json saved ({len(metadata)} tickers)")
        logger.info("=== Build Complete ===")
        
        # Record step completion
        self._record_step('build', len(metadata), 'completed')
    
    def cmd_run_all(self):
        """Execute all steps in sequence (the 'one button' command)."""
        logger.info("=" * 70)
        logger.info("=== 🚀 RUNNING FULL DATA PIPELINE ===")
        logger.info("=" * 70)
        
        if self.dry_run:
            logger.info("DRY RUN: Full pipeline simulation")
            logger.info("")
            
            # Show what each step would do by calling their dry-run methods
            logger.info("Step 1: Initialize database (if needed)")
            if not DB_PATH.exists():
                logger.info("  → Database would be created")
            else:
                logger.info("  → Database already exists, skipping")
            
            logger.info("")
            logger.info("Step 2: Sync FTP (download NASDAQ ticker lists)")
            # Temporarily create instance without dry_run to check status
            temp_cli = TickerCLI(dry_run=False)
            temp_cli.conn = self.conn
            today = get_today()
            conn = temp_cli.connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT sync_date FROM sync_history WHERE sync_date = ?", (today,))
            if cursor.fetchone():
                logger.info("  → Already synced today, would skip")
            else:
                logger.info("  → Would download nasdaqlisted.txt and otherlisted.txt")
                logger.info("  → Would parse and insert tickers into database")
            
            logger.info("")
            logger.info("Step 3: Extract prices (Pass 1 - price/volume)")
            cursor.execute("""
                SELECT COUNT(*) FROM tickers 
                WHERE is_etf = 0
                AND symbol NOT IN (
                    SELECT symbol FROM daily_metrics 
                    WHERE date = ? AND price IS NOT NULL
                )
            """, (today,))
            result = cursor.fetchone()
            pending = result[0] if result else 0
            if pending == 0:
                logger.info("  → All tickers already have price data, would skip")
            else:
                logger.info(f"  → Would fetch data for {pending} tickers")
                logger.info(f"  → Would process in batches of 100")
                logger.info(f"  → Estimated time: ~{pending * 1 / 100:.0f} minutes")
            
            logger.info("")
            logger.info("Step 4: Extract metadata (Pass 2 - detailed metrics)")
            cursor.execute("""
                SELECT COUNT(*) FROM daily_metrics
                WHERE date = ?
                AND price >= 5.0
                AND volume >= 100000
                AND market_cap IS NULL
            """, (today,))
            pending_meta = cursor.fetchone()[0]
            if pending_meta == 0:
                logger.info("  → All filtered tickers already have metadata, would skip")
            else:
                logger.info(f"  → Would fetch metadata for {pending_meta} filtered tickers")
                logger.info(f"  → Would collect: market cap, dividend yield, beta, RSI, MA200")
                logger.info(f"  → Estimated time: ~{pending_meta * 1.5 / 50:.0f} minutes")
            
            logger.info("")
            logger.info("Step 5: Build (generate JSON assets)")
            cursor.execute("""
                SELECT COUNT(*) FROM daily_metrics 
                WHERE date = ? AND price >= 5.0 AND volume >= 100000 AND market_cap IS NOT NULL
            """, (today,))
            ticker_count = cursor.fetchone()[0]
            logger.info(f"  → Would build from {ticker_count} tickers")
            logger.info(f"  → Would calculate 5 strategy scores via percentile ranking")
            logger.info(f"  → Would generate trie.json and metadata.json")
            
            logger.info("")
            logger.info("Step 6: Status report")
            logger.info("  → Would display comprehensive system status")
            
            logger.info("")
            logger.info("DRY RUN: No actual changes would be made")
            return
        
        # Initialize if needed (automatic)
        self._ensure_initialized()
        
        # Track success
        pipeline_failed = False
        failed_step = None
        
        try:
            # Sync FTP
            logger.info("")
            logger.info("📥 Step 1: Syncing FTP ticker lists...")
            self.cmd_sync_ftp()
            
            # Extract prices
            logger.info("")
            logger.info("💹 Step 2: Extracting price/volume data (Pass 1)...")
            self.cmd_extract_prices()
            
            # Extract metadata
            logger.info("")
            logger.info("📊 Step 3: Extracting metadata (Pass 2)...")
            self.cmd_extract_metadata()
            
            # Build assets
            logger.info("")
            logger.info("🔨 Step 4: Building JSON assets...")
            self.cmd_build()
            
        except Exception as e:
            pipeline_failed = True
            failed_step = "unknown"
            
            # Determine which step failed based on traceback or context
            import traceback
            tb = traceback.format_exc()
            if 'cmd_sync_ftp' in tb:
                failed_step = "sync-ftp"
            elif 'cmd_extract_prices' in tb:
                failed_step = "extract-prices"
            elif 'cmd_extract_metadata' in tb:
                failed_step = "extract-metadata"
            elif 'cmd_build' in tb:
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
            self._record_step(failed_step, 0, 'failed')
            
            # Re-raise to ensure non-zero exit code
            raise
        
        # Summary
        if not pipeline_failed:
            self._print_pipeline_summary()
            
            logger.info("")
            logger.info("=" * 70)
            logger.info("=== ✅ PIPELINE COMPLETE ===")
            logger.info("=" * 70)
    
    def cmd_reset(self, force=False):
        """Reset today's data (with confirmation)."""
        logger.info("=" * 70)
        logger.info("=== ⚠️  RESET TODAY'S DATA ===")
        logger.info("=" * 70)
        
        if not DB_PATH.exists():
            logger.info("No database found. Nothing to reset.")
            return
        
        conn = self.connect_db()
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
                return
            else:
                logger.info("⚠ No data found for today, but --force specified. Proceeding...")
        
        # Show what will be deleted
        logger.info("")
        logger.info("The following data for today ({}) will be DELETED:".format(today))
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
        files_to_delete = []
        
        if trie_path.exists():
            files_to_delete.append("trie.json")
            logger.warning(f"  ⚠ Output Files: trie.json ({trie_path.stat().st_size / 1024:.1f} KB)")
        
        if metadata_path.exists():
            files_to_delete.append("metadata.json")
            logger.warning(f"  ⚠ Output Files: metadata.json ({metadata_path.stat().st_size / 1024:.1f} KB)")
        
        if not files_to_delete and not ftp_synced and daily_metrics_count == 0 and scores_count == 0 and steps_count == 0:
            logger.info("")
            logger.info("✓ Nothing to delete.")
            return
        
        logger.info("")
        logger.info("⚠️  NOTE: Ticker list (from FTP) will NOT be deleted.")
        logger.info("   Only today's price data, metrics, scores, and output files.")
        logger.info("")
        
        # Prompt for confirmation
        if self.dry_run:
            logger.info("DRY RUN: Would prompt for confirmation and delete data")
            return
        
        try:
            response = input("Type 'yes' to confirm deletion: ").strip().lower()
            if response != 'yes':
                logger.info("Reset cancelled.")
                return
        except (KeyboardInterrupt, EOFError):
            logger.info("\nReset cancelled.")
            return
        
        # Perform deletion
        logger.info("")
        logger.info("Deleting data...")
        
        cursor.execute("DELETE FROM daily_metrics WHERE date = ?", (today,))
        deleted_metrics = cursor.rowcount
        logger.info(f"✓ Deleted {deleted_metrics} daily_metrics records")
        
        cursor.execute("DELETE FROM strategy_scores WHERE date = ?", (today,))
        deleted_scores = cursor.rowcount
        logger.info(f"✓ Deleted {deleted_scores} strategy_scores records")
        
        cursor.execute("DELETE FROM pipeline_steps WHERE run_date = ?", (today,))
        deleted_steps = cursor.rowcount
        logger.info(f"✓ Deleted {deleted_steps} pipeline_steps records")
        
        cursor.execute("DELETE FROM sync_history WHERE sync_date = ?", (today,))
        deleted_sync = cursor.rowcount
        logger.info(f"✓ Deleted {deleted_sync} sync_history records")
        
        conn.commit()
        
        # Delete output files
        for file_name in files_to_delete:
            file_path = API_DIR / file_name
            try:
                file_path.unlink()
                logger.info(f"✓ Deleted {file_name}")
            except Exception as e:
                logger.warning(f"⚠ Could not delete {file_name}: {e}")
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("=== ✅ RESET COMPLETE ===")
        logger.info("=" * 70)
        logger.info("")
        logger.info("You can now run: ./run.sh run-all")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Stock Market Ticker Discovery CLI - One Button Data Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  run-all           🚀 THE ONE BUTTON - Execute full pipeline (auto-initializes DB)
                    Sub-commands available for individual steps:
  
  sync-ftp          📥 Download ticker lists from NASDAQ FTP
  extract-prices    💹 Fetch price/volume for all tickers (Pass 1)
  extract-metadata  📊 Fetch detailed metrics for filtered tickers (Pass 2)
  build             🔨 Generate trie.json and metadata.json
  
  status            📋 Comprehensive system status (DB, network, data progress)
                    Shows step-by-step progress and recommends next action
  
  reset             ♻️  Reset today's data (with confirmation prompt)
  init              🗄️  Initialize database schema (usually automatic)

Examples:
  ./run.sh run-all              Run the full pipeline (one button!)
  ./run.sh run-all --dry-run    See what would happen without changes
  ./run.sh status               Check system health and get recommendations
  ./run.sh extract-prices       Re-run just the price extraction step
  ./run.sh reset                Clear today's data and start fresh
  ./run.sh reset --force        Force reset even if no data exists
        """
    )
    
    parser.add_argument('command', 
                        choices=['status', 'init', 'sync-ftp', 'extract-prices', 
                                'extract-metadata', 'build', 'run-all', 'reset'],
                        help='Command to execute')
    
    parser.add_argument('--dry-run', 
                        action='store_true',
                        help='Simulate command without making changes (not applicable to status)')
    
    parser.add_argument('--force',
                        action='store_true',
                        help='Force operation (for reset command)')
    
    args = parser.parse_args()
    
    # Dry-run not applicable to status
    dry_run = args.dry_run if args.command != 'status' else False
    
    cli = TickerCLI(dry_run=dry_run)
    
    try:
        if args.command == 'status':
            cli.cmd_status()
        elif args.command == 'init':
            cli.cmd_init()
        elif args.command == 'sync-ftp':
            cli.cmd_sync_ftp()
        elif args.command == 'extract-prices':
            cli.cmd_extract_prices()
        elif args.command == 'extract-metadata':
            cli.cmd_extract_metadata()
        elif args.command == 'build':
            cli.cmd_build()
        elif args.command == 'run-all':
            cli.cmd_run_all()
        elif args.command == 'reset':
            cli.cmd_reset(force=args.force)
    
    except KeyboardInterrupt:
        logger.info("\n⚠ Operation interrupted by user. Progress has been saved.")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        cli.close_db()


if __name__ == '__main__':
    main()
