"""
Pytest fixtures for stock-ticker CLI tests.

Provides reusable test fixtures for:
- Temporary databases
- Mock Yahoo Finance data
- Temporary file systems
- Sample data
"""
import json
import sqlite3
import tempfile
from pathlib import Path
from datetime import date
from typing import Generator
import pytest
import pandas as pd


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory that gets cleaned up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db(temp_dir: Path) -> Path:
    """Provide a temporary SQLite database."""
    db_path = temp_dir / "test_market_data.db"
    return db_path


@pytest.fixture
def initialized_db(temp_db: Path) -> Generator[Path, None, None]:
    """Provide an initialized database with schema."""
    # Read schema
    schema_path = Path(__file__).parent.parent / "schema.sql"
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # Initialize database
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()
    
    yield temp_db


@pytest.fixture
def sample_tickers() -> list[dict]:
    """Provide sample ticker data."""
    return [
        {
            'symbol': 'AAPL',
            'name': 'Apple Inc.',
            'exchange': 'NASDAQ',
            'is_etf': False
        },
        {
            'symbol': 'MSFT',
            'name': 'Microsoft Corporation',
            'exchange': 'NASDAQ',
            'is_etf': False
        },
        {
            'symbol': 'TSLA',
            'name': 'Tesla, Inc.',
            'exchange': 'NASDAQ',
            'is_etf': False
        },
        {
            'symbol': 'SPY',
            'name': 'SPDR S&P 500 ETF Trust',
            'exchange': 'NYSE',
            'is_etf': True
        },
    ]


@pytest.fixture
def sample_daily_metrics() -> list[dict]:
    """Provide sample daily metrics data."""
    today = date.today().isoformat()
    return [
        {
            'symbol': 'AAPL',
            'date': today,
            'price': 150.25,
            'volume': 50000000,
            'market_cap': 2500000000000,
            'dividend_yield': 0.0055,
            'beta': 1.2,
            'rsi_14': 55.0,
            'ma_200': 145.0
        },
        {
            'symbol': 'MSFT',
            'date': today,
            'price': 350.75,
            'volume': 30000000,
            'market_cap': 2600000000000,
            'dividend_yield': 0.0075,
            'beta': 0.9,
            'rsi_14': 60.0,
            'ma_200': 340.0
        },
    ]


@pytest.fixture
def populated_db(initialized_db: Path, sample_tickers: list[dict], 
                 sample_daily_metrics: list[dict]) -> Path:
    """Provide a database populated with sample data."""
    conn = sqlite3.connect(initialized_db)
    cursor = conn.cursor()
    
    # Insert tickers
    for ticker in sample_tickers:
        cursor.execute("""
            INSERT INTO tickers (symbol, name, exchange, is_etf)
            VALUES (?, ?, ?, ?)
        """, (ticker['symbol'], ticker['name'], ticker['exchange'], ticker['is_etf']))
    
    # Insert daily metrics
    for metric in sample_daily_metrics:
        cursor.execute("""
            INSERT INTO daily_metrics 
            (symbol, date, price, volume, market_cap, dividend_yield, beta, rsi_14, ma_200)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metric['symbol'], metric['date'], metric['price'], metric['volume'],
            metric['market_cap'], metric['dividend_yield'], metric['beta'],
            metric['rsi_14'], metric['ma_200']
        ))
    
    conn.commit()
    conn.close()
    
    return initialized_db


@pytest.fixture
def mock_yfinance_ticker(mocker):
    """Mock yfinance Ticker class."""
    mock_ticker = mocker.MagicMock()
    
    # Mock info property
    mock_ticker.info = {
        'marketCap': 2500000000000,
        'dividendYield': 0.0055,
        'beta': 1.2,
    }
    
    # Mock history method
    mock_history = pd.DataFrame({
        'Close': [150.0, 151.0, 149.5, 150.25] * 50,  # 200 days
        'Volume': [50000000] * 200,
    })
    mock_ticker.history.return_value = mock_history
    
    return mock_ticker


@pytest.fixture
def mock_yfinance_download(mocker):
    """Mock yfinance download function."""
    def _mock_download(tickers, period='1d', group_by='ticker', 
                      progress=False, threads=True):
        # Return DataFrame with price data for requested tickers
        symbols = tickers.split() if isinstance(tickers, str) else tickers
        
        if len(symbols) == 1:
            return pd.DataFrame({
                'Close': [150.25],
                'Volume': [50000000],
            })
        else:
            data = {}
            for symbol in symbols:
                data[symbol] = pd.DataFrame({
                    'Close': [150.25],
                    'Volume': [50000000],
                })
            return data
    
    return mocker.patch('yfinance.download', side_effect=_mock_download)


@pytest.fixture
def mock_ftp_server(mocker):
    """Mock FTP server connection."""
    mock_ftp = mocker.MagicMock()
    
    # Mock NASDAQ file content
    nasdaq_content = b"""Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
AAPL|Apple Inc. - Common Stock|Q|N|N|100|N|N
MSFT|Microsoft Corporation - Common Stock|Q|N|N|100|N|N
TSLA|Tesla, Inc. - Common Stock|Q|N|N|100|N|N
File Creation Time: 1234567890|
"""
    
    # Mock OTHER file content
    other_content = b"""ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
SPY|SPDR S&P 500 ETF Trust|A|SPY|Y|100|N|SPY
File Creation Time: 1234567890|
"""
    
    def mock_retrbinary(cmd, callback):
        if 'nasdaqlisted' in cmd:
            callback(nasdaq_content)
        elif 'otherlisted' in cmd:
            callback(other_content)
    
    mock_ftp.retrbinary.side_effect = mock_retrbinary
    
    return mocker.patch('ftplib.FTP', return_value=mock_ftp)


@pytest.fixture
def temp_hugo_dir(temp_dir: Path) -> Path:
    """Create a temporary Hugo-like directory structure."""
    hugo_dir = temp_dir / "hugo" / "site" / "static" / "data"
    hugo_dir.mkdir(parents=True, exist_ok=True)
    return hugo_dir


@pytest.fixture
def sample_strategy_scores() -> list[dict]:
    """Provide sample strategy scores."""
    today = date.today().isoformat()
    return [
        {
            'symbol': 'AAPL',
            'date': today,
            'dividend_daddy_score': 85,
            'moon_shot_score': 45,
            'falling_knife_score': 20,
            'over_hyped_score': 75,
            'inst_whale_score': 95
        },
        {
            'symbol': 'MSFT',
            'date': today,
            'dividend_daddy_score': 90,
            'moon_shot_score': 35,
            'falling_knife_score': 15,
            'over_hyped_score': 80,
            'inst_whale_score': 98
        },
    ]


def assert_valid_json_file(filepath: Path) -> dict:
    """
    Assert that a file exists and contains valid JSON.
    Returns the parsed JSON data.
    """
    assert filepath.exists(), f"File does not exist: {filepath}"
    
    with open(filepath, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {filepath}: {e}")
    
    return data


def assert_json_structure(data: dict, required_keys: list[str]):
    """Assert that JSON data has required keys."""
    missing_keys = [key for key in required_keys if key not in data]
    assert not missing_keys, f"Missing required keys: {missing_keys}"
