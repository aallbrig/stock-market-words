"""
Configuration and constants for the stock ticker CLI.
"""
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
DB_PATH = BASE_DIR / "data" / "market_data.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"
TMP_DIR = BASE_DIR / "data" / "tmp"
API_DIR = BASE_DIR / "hugo" / "static" / "api"
ERROR_LOG_PATH = BASE_DIR / "data" / "error.log"

# Ensure directories exist
TMP_DIR.mkdir(parents=True, exist_ok=True)
API_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Processing configuration
PRICE_BATCH_SIZE = 100
METADATA_BATCH_SIZE = 50

# Filtering thresholds
MIN_PRICE = 5.0
MIN_VOLUME = 100000

# FTP configuration
FTP_HOST = "ftp.nasdaqtrader.com"
FTP_PATH = "/SymbolDirectory/"
FTP_FILES = ["nasdaqlisted.txt", "otherlisted.txt"]

# Yahoo Finance configuration
YAHOO_API_HOST = "query1.finance.yahoo.com"

# Exponential backoff configuration
BACKOFF_INITIAL_DELAY = 0.5  # seconds
BACKOFF_MAX_DELAY = 300  # 5 minutes in seconds (configurable)
BACKOFF_MULTIPLIER = 2.0
