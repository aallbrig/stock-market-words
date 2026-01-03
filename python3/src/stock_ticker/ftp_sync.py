"""
FTP synchronization for downloading ticker lists from NASDAQ.
"""
import sys
from ftplib import FTP
from pathlib import Path
import pandas as pd
import re
from .config import FTP_HOST, FTP_PATH, FTP_FILES, TMP_DIR
from .utils import get_today, is_valid_symbol
from .database import get_connection, record_pipeline_step
from .logging_setup import setup_logging

logger = setup_logging()

# Exchange code mapping for otherlisted.txt
EXCHANGE_MAP = {
    'A': 'NYSE MKT',
    'N': 'NYSE',
    'P': 'NYSE ARCA',
    'Z': 'BATS',
    'V': 'IEX'
}

# Keywords that indicate non-common-stock securities
# Use word boundaries to avoid false positives
DERIVATIVE_KEYWORDS = [
    r'\bUnit\b', r'\bUnits\b',  # Units
    r'\bWarrant\b', r'\bWarrants\b',  # Warrants
    r'\bPreferred Stock\b',  # Preferred (specific phrase)
    r'\bSeries [A-Z]\b',  # Series A, Series B, etc.
    r'\bDepositary Shares\b', r'\bAmerican Depositary Shares\b',  # Specific ADS
    r'\bRight\b', r'\bRights\b',  # Rights
    r'\bTrust Preferred\b',  # Trust Preferred Securities
    r'\bCumulative Preferred\b'  # Cumulative Preferred
]


def _contains_derivative_keywords(name):
    """Check if security name contains derivative keywords using regex patterns."""
    if pd.isna(name):
        return False
    name_str = str(name)
    for pattern in DERIVATIVE_KEYWORDS:
        if re.search(pattern, name_str, re.IGNORECASE):
            return True
    return False


def sync_ftp(dry_run=False):
    """Download and parse ticker lists from NASDAQ FTP."""
    if dry_run:
        logger.info("DRY RUN: Would sync ticker lists from ftp.nasdaqtrader.com")
        logger.info("DRY RUN: Would download nasdaqlisted.txt")
        logger.info("DRY RUN: Would download otherlisted.txt")
        logger.info("DRY RUN: Would parse and insert tickers into database")
        return
    
    logger.info("Syncing ticker lists from ftp.nasdaqtrader.com...")
    
    conn = get_connection()
    cursor = conn.cursor()
    today = get_today()
    
    # Check if already synced today
    cursor.execute("SELECT sync_date FROM sync_history WHERE sync_date = ?", (today,))
    if cursor.fetchone():
        logger.info(f"✓ FTP already synced today ({today}). Skipping.")
        conn.close()
        return
    
    tickers_added = 0
    
    # Download files
    nasdaq_file = TMP_DIR / "nasdaqlisted.txt"
    other_file = TMP_DIR / "otherlisted.txt"
    
    try:
        logger.info("Connecting to ftp.nasdaqtrader.com...")
        ftp = FTP(FTP_HOST, timeout=30)
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
        conn.close()
        sys.exit(1)
    
    # Parse nasdaqlisted.txt
    logger.info("Parsing nasdaqlisted.txt...")
    try:
        df_nasdaq = pd.read_csv(nasdaq_file, sep='|')
        df_nasdaq = df_nasdaq[df_nasdaq['Symbol'].notna()]
        df_nasdaq = df_nasdaq[:-1]  # Remove last row (file metadata)
        
        # Apply filtering rules for NASDAQ
        logger.info(f"  Total rows in nasdaqlisted.txt: {len(df_nasdaq)}")
        
        # Filter 1: Test Issue must be 'N'
        df_nasdaq = df_nasdaq[df_nasdaq['Test Issue'] == 'N']
        logger.info(f"  After removing test issues: {len(df_nasdaq)}")
        
        # Filter 2: ETF must be 'N' (we want common stocks only)
        df_nasdaq = df_nasdaq[df_nasdaq['ETF'] == 'N']
        logger.info(f"  After removing ETFs: {len(df_nasdaq)}")
        
        # Filter 2.5: Remove ETNs (Exchange Traded Notes) by name
        df_nasdaq = df_nasdaq[~df_nasdaq['Security Name'].str.contains('ETN', case=False, na=False)]
        logger.info(f"  After removing ETNs: {len(df_nasdaq)}")
        
        # Filter 3: Financial Status must be 'N' (Normal)
        if 'Financial Status' in df_nasdaq.columns:
            df_nasdaq = df_nasdaq[df_nasdaq['Financial Status'] == 'N']
            logger.info(f"  After removing non-normal financial status: {len(df_nasdaq)}")
        
        # Filter 4: Remove derivatives by keyword in Security Name
        mask = df_nasdaq['Security Name'].apply(_contains_derivative_keywords)
        df_nasdaq = df_nasdaq[~mask]
        logger.info(f"  After removing derivatives by keyword: {len(df_nasdaq)}")
        
        # Filter 5: Symbol validation (1-5 uppercase letters, no W/R/U/P/Q/F suffixes)
        df_nasdaq = df_nasdaq[df_nasdaq['Symbol'].apply(is_valid_symbol)]
        logger.info(f"  After symbol validation: {len(df_nasdaq)}")
        
        # Batch insert preparation
        ticker_data = []
        for _, row in df_nasdaq.iterrows():
            symbol = str(row['Symbol']).strip()
            name = str(row.get('Security Name', '')).strip()
            ticker_data.append((symbol, name, 'NASDAQ', False))
        
        # Batch insert
        if ticker_data:
            cursor.executemany("""
                INSERT OR IGNORE INTO tickers (symbol, name, exchange, is_etf)
                VALUES (?, ?, ?, ?)
            """, ticker_data)
            tickers_added += cursor.rowcount
        
        logger.info(f"Processed {len(df_nasdaq)} NASDAQ tickers.")
    
    except Exception as e:
        logger.error(f"Failed to parse nasdaqlisted.txt: {e}")
    
    # Parse otherlisted.txt
    logger.info("Parsing otherlisted.txt...")
    try:
        df_other = pd.read_csv(other_file, sep='|')
        df_other = df_other[df_other['ACT Symbol'].notna()]
        df_other = df_other[:-1]  # Remove last row
        
        logger.info(f"  Total rows in otherlisted.txt: {len(df_other)}")
        
        # Filter 1: Test Issue must be 'N'
        df_other = df_other[df_other['Test Issue'] == 'N']
        logger.info(f"  After removing test issues: {len(df_other)}")
        
        # Filter 2: ETF must be 'N' 
        df_other = df_other[df_other['ETF'] == 'N']
        logger.info(f"  After removing ETFs: {len(df_other)}")
        
        # Filter 2.5: Remove ETNs (Exchange Traded Notes) by name
        df_other = df_other[~df_other['Security Name'].str.contains('ETN', case=False, na=False)]
        logger.info(f"  After removing ETNs: {len(df_other)}")
        
        # Filter 3: Remove derivatives by keyword in Security Name
        mask = df_other['Security Name'].apply(_contains_derivative_keywords)
        df_other = df_other[~mask]
        logger.info(f"  After removing derivatives by keyword: {len(df_other)}")
        
        # Filter 4: Symbol validation (1-5 uppercase letters, no W/R/U/P/Q/F suffixes)
        df_other = df_other[df_other['ACT Symbol'].apply(is_valid_symbol)]
        logger.info(f"  After symbol validation: {len(df_other)}")
        
        # Batch insert preparation with exchange mapping
        ticker_data = []
        for _, row in df_other.iterrows():
            symbol = str(row['ACT Symbol']).strip()
            name = str(row.get('Security Name', '')).strip()
            exchange_code = str(row.get('Exchange', 'OTHER')).strip()
            
            # Map exchange code to human-readable name
            exchange = EXCHANGE_MAP.get(exchange_code, exchange_code)
            
            ticker_data.append((symbol, name, exchange, False))
        
        # Batch insert
        if ticker_data:
            cursor.executemany("""
                INSERT OR IGNORE INTO tickers (symbol, name, exchange, is_etf)
                VALUES (?, ?, ?, ?)
            """, ticker_data)
            tickers_added += cursor.rowcount
        
        logger.info(f"Processed {len(df_other)} other exchange tickers.")
    
    except Exception as e:
        logger.error(f"Failed to parse otherlisted.txt: {e}")
    
    # Record sync in history (only after successful batch inserts)
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO sync_history (sync_date, tickers_synced)
            VALUES (?, ?)
        """, (today, tickers_added))
        
        conn.commit()
        logger.info(f"✓ FTP sync complete. {tickers_added} new tickers added.")
        
        # Record step completion
        record_pipeline_step('sync-ftp', tickers_added, 'completed', dry_run=False)
        
    except Exception as e:
        logger.error(f"Failed to commit sync results: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
