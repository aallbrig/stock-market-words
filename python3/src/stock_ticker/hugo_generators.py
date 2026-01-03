"""
Hugo site content generators.
Generate data files and markdown pages for the Hugo site based on SQLite database.
"""
import json
import csv
from pathlib import Path
from datetime import datetime
from .config import DB_PATH, BASE_DIR, TMP_DIR
from .database import get_connection
from .utils import get_today
from .logging_setup import setup_logging

logger = setup_logging()

# Hugo site paths
HUGO_SITE_DIR = BASE_DIR / "hugo" / "site"
HUGO_DATA_DIR = HUGO_SITE_DIR / "static" / "data"  # Use static/data to avoid Hugo parsing
HUGO_CONTENT_DIR = HUGO_SITE_DIR / "content"


def ensure_hugo_dirs():
    """Ensure Hugo directories exist."""
    HUGO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    HUGO_CONTENT_DIR.mkdir(parents=True, exist_ok=True)


def generate_raw_ftp_data(dry_run=False):
    """
    Generate JSON/CSV files showing raw FTP data BEFORE filtering.
    
    Uses the last downloaded FTP files from TMP_DIR to show what came from NASDAQ.
    Includes table headers and all rows.
    """
    if dry_run:
        logger.info("DRY RUN: Would generate raw FTP data files")
        logger.info(f"DRY RUN: Output to {HUGO_DATA_DIR}")
        logger.info("DRY RUN: Files: raw_nasdaq.json, raw_otherlisted.json")
        return
    
    logger.info("=== Generating Raw FTP Data ===")
    ensure_hugo_dirs()
    
    import pandas as pd
    
    nasdaq_file = TMP_DIR / "nasdaqlisted.txt"
    other_file = TMP_DIR / "otherlisted.txt"
    
    if not nasdaq_file.exists() or not other_file.exists():
        logger.warning("FTP files not found in tmp/. Run sync-ftp first.")
        return
    
    # Parse NASDAQ file
    logger.info("Processing nasdaqlisted.txt...")
    try:
        df_nasdaq = pd.read_csv(nasdaq_file, sep='|')
        df_nasdaq = df_nasdaq[df_nasdaq['Symbol'].notna()]
        
        # Convert to records (includes all columns)
        nasdaq_data = {
            'source': 'NASDAQ FTP',
            'file': 'nasdaqlisted.txt',
            'downloaded_at': datetime.now().isoformat(),
            'total_rows': len(df_nasdaq),
            'columns': list(df_nasdaq.columns),
            'data': df_nasdaq.to_dict('records')
        }
        
        output_path = HUGO_DATA_DIR / "raw_nasdaq.json"
        with open(output_path, 'w') as f:
            json.dump(nasdaq_data, f, indent=2, default=str)
        
        logger.info(f"✓ Written: {output_path} ({len(df_nasdaq)} rows)")
        
    except Exception as e:
        logger.error(f"Failed to process nasdaqlisted.txt: {e}")
    
    # Parse otherlisted file
    logger.info("Processing otherlisted.txt...")
    try:
        df_other = pd.read_csv(other_file, sep='|')
        df_other = df_other[df_other['ACT Symbol'].notna()]
        
        other_data = {
            'source': 'NASDAQ FTP',
            'file': 'otherlisted.txt',
            'downloaded_at': datetime.now().isoformat(),
            'total_rows': len(df_other),
            'columns': list(df_other.columns),
            'data': df_other.to_dict('records')
        }
        
        output_path = HUGO_DATA_DIR / "raw_otherlisted.json"
        with open(output_path, 'w') as f:
            json.dump(other_data, f, indent=2, default=str)
        
        logger.info(f"✓ Written: {output_path} ({len(df_other)} rows)")
        
    except Exception as e:
        logger.error(f"Failed to process otherlisted.txt: {e}")
    
    logger.info("✓ Raw FTP data generation complete")


def generate_filtered_data(dry_run=False):
    """
    Generate JSON files showing filtered data AFTER Pass 1 (price extraction).
    
    Shows:
    - All tickers that passed filtering and are in the database
    - Their current price/volume data (if available)
    - Filtering statistics
    """
    if dry_run:
        logger.info("DRY RUN: Would generate filtered ticker data")
        logger.info(f"DRY RUN: Output to {HUGO_DATA_DIR}")
        logger.info("DRY RUN: Files: filtered_tickers.json, pass1_results.json")
        return
    
    logger.info("=== Generating Filtered Data ===")
    ensure_hugo_dirs()
    
    conn = get_connection()
    cursor = conn.cursor()
    today = get_today()
    
    # Get all tickers in database (these passed filtering)
    logger.info("Querying filtered tickers...")
    cursor.execute("""
        SELECT 
            t.symbol,
            t.name,
            t.exchange,
            t.is_etf,
            t.first_seen,
            dm.date as price_date,
            dm.price,
            dm.volume,
            dm.market_cap,
            dm.dividend_yield,
            dm.beta,
            dm.rsi_14,
            dm.ma_200
        FROM tickers t
        LEFT JOIN daily_metrics dm ON t.symbol = dm.symbol AND dm.date = ?
        ORDER BY t.exchange, t.symbol
    """, (today,))
    
    rows = cursor.fetchall()
    
    # Build filtered data structure
    filtered_data = {
        'generated_at': datetime.now().isoformat(),
        'date': today,
        'total_tickers': len(rows),
        'exchanges': {},
        'tickers': []
    }
    
    exchange_counts = {}
    
    for row in rows:
        ticker_data = {
            'symbol': row[0],
            'name': row[1],
            'exchange': row[2],
            'is_etf': bool(row[3]),
            'first_seen': row[4],
            'price_data': {
                'date': row[5],
                'price': row[6],
                'volume': row[7],
                'market_cap': row[8],
                'dividend_yield': row[9],
                'beta': row[10],
                'rsi_14': row[11],
                'ma_200': row[12]
            } if row[5] else None
        }
        
        filtered_data['tickers'].append(ticker_data)
        
        # Count by exchange
        exchange = row[2]
        exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
    
    filtered_data['exchanges'] = exchange_counts
    
    # Get filtering statistics
    cursor.execute("SELECT COUNT(*) FROM tickers")
    total_filtered = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = ? AND price IS NOT NULL", (today,))
    with_price = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = ? AND market_cap IS NOT NULL", (today,))
    with_metadata = cursor.fetchone()[0]
    
    filtered_data['statistics'] = {
        'total_tickers_in_db': total_filtered,
        'with_price_data': with_price,
        'with_metadata': with_metadata,
        'by_exchange': exchange_counts
    }
    
    conn.close()
    
    # Write filtered tickers
    output_path = HUGO_DATA_DIR / "filtered_tickers.json"
    with open(output_path, 'w') as f:
        json.dump(filtered_data, f, indent=2, default=str)
    
    logger.info(f"✓ Written: {output_path} ({len(rows)} tickers)")
    
    # Generate Pass 1 results summary
    pass1_data = {
        'generated_at': datetime.now().isoformat(),
        'date': today,
        'pass1_extraction': {
            'total_attempted': total_filtered,
            'successful': with_price,
            'failed': total_filtered - with_price,
            'success_rate': f"{(with_price / total_filtered * 100):.1f}%" if total_filtered > 0 else "0%"
        },
        'pass2_extraction': {
            'total_attempted': with_price,
            'successful': with_metadata,
            'pending': with_price - with_metadata
        }
    }
    
    output_path = HUGO_DATA_DIR / "pass1_results.json"
    with open(output_path, 'w') as f:
        json.dump(pass1_data, f, indent=2)
    
    logger.info(f"✓ Written: {output_path}")
    logger.info("✓ Filtered data generation complete")


def generate_hugo_pages(dry_run=False):
    """
    Generate Hugo markdown pages for displaying the data.
    
    Creates:
    - raw-ftp-data.md: Page to display raw FTP data
    - filtered-data.md: Page to display filtered ticker data
    """
    if dry_run:
        logger.info("DRY RUN: Would generate Hugo markdown pages")
        logger.info(f"DRY RUN: Output to {HUGO_CONTENT_DIR}")
        return
    
    logger.info("=== Generating Hugo Pages ===")
    ensure_hugo_dirs()
    
    # Page 1: Raw FTP Data
    raw_ftp_page = """---
title: "Raw FTP Data"
description: "Raw ticker data from NASDAQ FTP before any filtering"
date: {}
type: "page"
layout: "raw-data"
---

This page shows the raw ticker data downloaded from NASDAQ FTP servers **before** any filtering is applied.

## Data Sources

- **nasdaqlisted.txt**: All NASDAQ-listed securities
- **otherlisted.txt**: Securities listed on other exchanges (NYSE, AMEX, etc.)

The data includes test tickers, ETFs, warrants, units, preferred stock, and all other security types.

""".format(datetime.now().isoformat())
    
    output_path = HUGO_CONTENT_DIR / "raw-ftp-data.md"
    with open(output_path, 'w') as f:
        f.write(raw_ftp_page)
    logger.info(f"✓ Written: {output_path}")
    
    # Page 2: Filtered Data
    filtered_page = """---
title: "Filtered Ticker Data"
description: "Ticker data after Pass 1 filtering and price extraction"
date: {}
type: "page"
layout: "filtered-data"
---

This page shows the ticker data **after** filtering has been applied.

## Filtering Pipeline

1. **Test Issue Filter**: Removes test tickers (ZZZZ, TEST, etc.)
2. **ETF Filter**: Removes ETFs (common stocks only)
3. **Financial Status Filter**: Removes bankrupt/deficient tickers
4. **Keyword Filter**: Removes Units, Warrants, Rights, Preferred Stock
5. **Symbol Validation**: Removes invalid symbols and suffixes

## Pass 1: Price Extraction

After filtering, price/volume data is extracted from Yahoo Finance for all remaining tickers.

""".format(datetime.now().isoformat())
    
    output_path = HUGO_CONTENT_DIR / "filtered-data.md"
    with open(output_path, 'w') as f:
        f.write(filtered_page)
    logger.info(f"✓ Written: {output_path}")
    
    logger.info("✓ Hugo page generation complete")


def generate_all_hugo_content(dry_run=False):
    """Generate all Hugo site content."""
    if dry_run:
        logger.info("DRY RUN: Would generate all Hugo content")
        logger.info("DRY RUN: - Raw FTP data")
        logger.info("DRY RUN: - Filtered ticker data")
        logger.info("DRY RUN: - Hugo markdown pages")
        return
    
    logger.info("======================================================================")
    logger.info("=== 📝 GENERATING HUGO SITE CONTENT ===")
    logger.info("======================================================================")
    logger.info("")
    
    # Generate raw FTP data
    logger.info("Step 1: Generating raw FTP data...")
    generate_raw_ftp_data(dry_run=False)
    logger.info("")
    
    # Generate filtered data
    logger.info("Step 2: Generating filtered ticker data...")
    generate_filtered_data(dry_run=False)
    logger.info("")
    
    # Generate Hugo pages
    logger.info("Step 3: Generating Hugo markdown pages...")
    generate_hugo_pages(dry_run=False)
    logger.info("")
    
    logger.info("======================================================================")
    logger.info("=== ✅ HUGO CONTENT GENERATION COMPLETE ===")
    logger.info("======================================================================")
    logger.info(f"Content location: {HUGO_SITE_DIR}")
    logger.info(f"Data files: {HUGO_DATA_DIR}")
    logger.info(f"Pages: {HUGO_CONTENT_DIR}")
