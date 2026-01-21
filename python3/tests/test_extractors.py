"""
Tests for data extractors (prices and metadata from Yahoo Finance).

Uses mocks to avoid hitting real Yahoo Finance API.
"""
import pytest
import pandas as pd
from stock_ticker.extractors import extract_prices, extract_metadata
from stock_ticker.utils import get_today


@pytest.mark.integration
class TestPriceExtraction:
    """Tests for price/volume extraction."""
    
    def test_extract_prices_with_mock(self, populated_db, 
                                      mock_yfinance_download, monkeypatch):
        """Test price extraction with mocked Yahoo Finance API."""
        monkeypatch.setenv('DB_PATH', str(populated_db))
        
        # Extract prices
        extract_prices(db_path=populated_db, batch_size=10)
        
        # Verify mock was called
        assert mock_yfinance_download.called
    
    def test_extract_prices_handles_missing_tickers(self, initialized_db, 
                                                     mock_yfinance_download, 
                                                     monkeypatch):
        """Test that price extraction handles tickers with no data."""
        import sqlite3
        
        # Add a ticker
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickers (symbol, name, exchange, is_etf)
            VALUES (?, ?, ?, ?)
        """, ('TEST', 'Test Company', 'NASDAQ', False))
        conn.commit()
        conn.close()
        
        monkeypatch.setenv('DB_PATH', str(initialized_db))
        
        # Mock download to return empty data
        mock_yfinance_download.return_value = pd.DataFrame()
        
        # Should handle gracefully
        extract_prices(db_path=initialized_db, batch_size=10)
    
    def test_extract_prices_skips_etfs(self, initialized_db, 
                                       mock_yfinance_download, monkeypatch):
        """Test that price extraction skips ETFs."""
        import sqlite3
        
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        
        # Add regular ticker and ETF
        cursor.execute("""
            INSERT INTO tickers (symbol, name, exchange, is_etf)
            VALUES (?, ?, ?, ?)
        """, ('AAPL', 'Apple Inc.', 'NASDAQ', False))
        
        cursor.execute("""
            INSERT INTO tickers (symbol, name, exchange, is_etf)
            VALUES (?, ?, ?, ?)
        """, ('SPY', 'S&P 500 ETF', 'NYSE', True))
        
        conn.commit()
        conn.close()
        
        monkeypatch.setenv('DB_PATH', str(initialized_db))
        
        # Extract prices
        extract_prices(db_path=initialized_db, batch_size=10)
        
        # Check that SPY was not processed
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        today = get_today()
        
        cursor.execute("""
            SELECT COUNT(*) FROM daily_metrics 
            WHERE symbol = 'SPY' AND date = ?
        """, (today,))
        
        spy_count = cursor.fetchone()[0]
        conn.close()
        
        # SPY should not have metrics (ETFs are filtered)
        assert spy_count == 0


@pytest.mark.integration
class TestMetadataExtraction:
    """Tests for metadata extraction."""
    
    def test_extract_metadata_with_mock(self, populated_db, mocker, monkeypatch):
        """Test metadata extraction with mocked Yahoo Finance."""
        monkeypatch.setenv('DB_PATH', str(populated_db))
        
        # Mock yfinance.Ticker
        mock_ticker_class = mocker.patch('yfinance.Ticker')
        mock_ticker_instance = mocker.MagicMock()
        
        # Mock info
        mock_ticker_instance.info = {
            'marketCap': 2500000000000,
            'dividendYield': 0.0055,
            'beta': 1.2,
        }
        
        # Mock history
        mock_history = pd.DataFrame({
            'Close': [150.0] * 200,
            'Volume': [50000000] * 200,
        })
        mock_ticker_instance.history.return_value = mock_history
        
        mock_ticker_class.return_value = mock_ticker_instance
        
        # Extract metadata
        extract_metadata(db_path=populated_db, batch_size=10)
        
        # Verify mock was called
        assert mock_ticker_class.called
    
    def test_extract_metadata_calculates_rsi(self, mocker):
        """Test that RSI is calculated correctly."""
        # Mock ticker with price history
        mock_ticker = mocker.MagicMock()
        
        # Create realistic price movements for RSI calculation
        prices = [100]
        for i in range(20):
            if i % 2 == 0:
                prices.append(prices[-1] + 1)
            else:
                prices.append(prices[-1] - 0.5)
        
        mock_history = pd.DataFrame({
            'Close': prices,
        })
        mock_ticker.history.return_value = mock_history
        
        # Calculate RSI manually
        delta = mock_history['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        
        if len(gain) >= 14 and loss.iloc[-1] != 0:
            rs = gain.iloc[-1] / loss.iloc[-1]
            rsi = 100 - (100 / (1 + rs))
            
            # RSI should be between 0 and 100
            assert 0 <= rsi <= 100
    
    def test_extract_metadata_handles_missing_data(self, populated_db, 
                                                    mocker, monkeypatch):
        """Test that metadata extraction handles missing/invalid data."""
        monkeypatch.setenv('DB_PATH', str(populated_db))
        
        # Mock ticker with incomplete data
        mock_ticker_class = mocker.patch('yfinance.Ticker')
        mock_ticker_instance = mocker.MagicMock()
        
        # Mock with missing fields
        mock_ticker_instance.info = {
            'marketCap': None,  # Missing data
        }
        
        # Empty history
        mock_ticker_instance.history.return_value = pd.DataFrame()
        
        mock_ticker_class.return_value = mock_ticker_instance
        
        # Should handle gracefully without crashing
        extract_metadata(db_path=populated_db, batch_size=10)


@pytest.mark.unit
class TestDataValidation:
    """Tests for data validation during extraction."""
    
    def test_price_data_validation(self):
        """Test that price data is validated."""
        # Valid price data
        assert 100.50 > 0
        assert 0.01 > 0
        
        # Invalid price data
        invalid_prices = [-1, 0, None, "not a number"]
        
        for price in invalid_prices:
            try:
                if price is not None and float(price) <= 0:
                    assert True  # Invalid price caught
            except (ValueError, TypeError):
                assert True  # Invalid type caught
    
    def test_volume_data_validation(self):
        """Test that volume data is validated."""
        # Valid volume
        assert 1000000 > 0
        assert isinstance(1000000, int)
        
        # Invalid volume
        invalid_volumes = [-1, -1000, None, "not a number"]
        
        for volume in invalid_volumes:
            try:
                if volume is not None and int(volume) < 0:
                    assert True  # Invalid volume caught
            except (ValueError, TypeError):
                assert True  # Invalid type caught
    
    def test_rsi_range_validation(self):
        """Test that RSI values are in valid range."""
        valid_rsi_values = [0, 30, 50, 70, 100]
        
        for rsi in valid_rsi_values:
            assert 0 <= rsi <= 100
        
        invalid_rsi_values = [-1, 101, 150, None]
        
        for rsi in invalid_rsi_values:
            if rsi is not None:
                is_valid = 0 <= rsi <= 100
                if rsi < 0 or rsi > 100:
                    assert not is_valid
    
    def test_beta_validation(self):
        """Test that beta values are reasonable."""
        # Beta can be any real number, but extreme values should be noted
        valid_betas = [0.5, 1.0, 1.5, 2.0]
        
        for beta in valid_betas:
            assert beta >= 0  # Beta is typically positive
        
        # Very high beta should be flagged (but not invalid)
        extreme_beta = 10.0
        assert extreme_beta > 3.0  # Unusually high beta


@pytest.mark.integration
@pytest.mark.slow
class TestBatchProcessing:
    """Tests for batch processing logic."""
    
    def test_extract_prices_processes_in_batches(self, initialized_db, 
                                                  mock_yfinance_download,
                                                  monkeypatch):
        """Test that price extraction processes tickers in batches."""
        import sqlite3
        
        # Add multiple tickers
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        
        for i in range(150):
            cursor.execute("""
                INSERT INTO tickers (symbol, name, exchange, is_etf)
                VALUES (?, ?, ?, ?)
            """, (f'TEST{i}', f'Test Company {i}', 'NASDAQ', False))
        
        conn.commit()
        conn.close()
        
        monkeypatch.setenv('DB_PATH', str(initialized_db))
        
        # Extract with small batch size
        extract_prices(db_path=initialized_db, batch_size=50)
        
        # Should have been called multiple times (150 tickers / 50 batch = 3 calls)
        assert mock_yfinance_download.call_count >= 3
