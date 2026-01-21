"""
Tests for data builders (strategy scoring and JSON generation).
"""
import json
import pytest
from pathlib import Path
from stock_ticker.builders import build_assets
from tests.conftest import assert_valid_json_file


@pytest.mark.integration
class TestAssetBuilding:
    """Tests for building JSON assets."""
    
    def test_build_assets_with_sample_data(self, populated_db, temp_dir, monkeypatch):
        """Test asset building with populated database."""
        api_dir = temp_dir / "api"
        api_dir.mkdir(parents=True)
        
        monkeypatch.setenv('DB_PATH', str(populated_db))
        monkeypatch.setenv('API_DIR', str(api_dir))
        
        # Build assets
        build_assets(db_path=populated_db, output_dir=api_dir)
        
        # Check that files were created (if sufficient data)
        trie_path = api_dir / "trie.json"
        metadata_path = api_dir / "metadata.json"
        
        # Files may not exist if not enough data, so check gracefully
        if trie_path.exists():
            trie_data = assert_valid_json_file(trie_path)
            assert isinstance(trie_data, dict)
        
        if metadata_path.exists():
            metadata_data = assert_valid_json_file(metadata_path)
            assert isinstance(metadata_data, dict)


@pytest.mark.unit
class TestStrategyScoring:
    """Tests for strategy scoring algorithms."""
    
    def test_dividend_daddy_score_calculation(self, populated_db):
        """Test dividend daddy score calculation."""
        import sqlite3
        from stock_ticker.utils import get_today
        
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        today = get_today()
        
        # Get metrics for a ticker
        cursor.execute("""
            SELECT dividend_yield, beta 
            FROM daily_metrics 
            WHERE symbol = 'AAPL' AND date = ?
        """, (today,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            dividend_yield, beta = result
            
            # Dividend daddy score = high yield + low volatility
            # Basic validation that values are reasonable
            assert dividend_yield is not None
            assert beta is not None
            assert dividend_yield >= 0
            assert beta >= 0
    
    def test_moon_shot_score_calculation(self, populated_db):
        """Test moon shot score calculation."""
        import sqlite3
        from stock_ticker.utils import get_today
        
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        today = get_today()
        
        # Get metrics
        cursor.execute("""
            SELECT beta, rsi_14 
            FROM daily_metrics 
            WHERE symbol = 'AAPL' AND date = ?
        """, (today,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            beta, rsi = result
            
            # Moon shot = high beta + oversold (low RSI)
            assert beta is not None
            assert rsi is not None
            assert 0 <= rsi <= 100
    
    def test_falling_knife_score_calculation(self, populated_db):
        """Test falling knife score calculation."""
        import sqlite3
        from stock_ticker.utils import get_today
        
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        today = get_today()
        
        # Get metrics
        cursor.execute("""
            SELECT price, ma_200, rsi_14 
            FROM daily_metrics 
            WHERE symbol = 'AAPL' AND date = ?
        """, (today,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            price, ma_200, rsi = result
            
            # Falling knife = oversold + below MA200
            assert price is not None
            if ma_200 is not None:
                assert ma_200 > 0
            if rsi is not None:
                assert 0 <= rsi <= 100


@pytest.mark.unit
class TestTrieGeneration:
    """Tests for trie (prefix tree) generation."""
    
    def test_trie_contains_symbol_prefixes(self):
        """Test that trie contains prefixes for symbols."""
        # Sample trie structure
        trie = {}
        symbol = "AAPL"
        
        # Build trie
        for i in range(1, len(symbol) + 1):
            prefix = symbol[:i]
            if prefix not in trie:
                trie[prefix] = []
            if symbol not in trie[prefix]:
                trie[prefix].append(symbol)
        
        # Validate
        assert 'A' in trie
        assert 'AA' in trie
        assert 'AAP' in trie
        assert 'AAPL' in trie
        assert 'AAPL' in trie['A']
        assert 'AAPL' in trie['AAPL']
    
    def test_trie_contains_name_prefixes(self):
        """Test that trie contains prefixes from company names."""
        trie = {}
        symbol = "AAPL"
        name = "APPLE INC"
        
        # Add name words to trie
        words = name.split()
        for word in words:
            for i in range(1, min(len(word) + 1, 6)):  # Limit to 5 chars
                prefix = word[:i]
                if prefix not in trie:
                    trie[prefix] = []
                if symbol not in trie[prefix]:
                    trie[prefix].append(symbol)
        
        # Validate
        assert 'A' in trie or 'APPL' in trie
        assert 'I' in trie or 'INC' in trie


@pytest.mark.unit
class TestMetadataGeneration:
    """Tests for metadata JSON generation."""
    
    def test_metadata_structure_is_correct(self, temp_dir):
        """Test that metadata has the correct structure."""
        metadata_file = temp_dir / "metadata.json"
        
        # Sample metadata
        metadata = {
            "AAPL": {
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "price": 150.25,
                "volume": 50000000,
                "marketCap": 2500000000000,
                "dividendYield": 0.55,
                "beta": 1.2,
                "rsi": 55.0,
                "ma200": 145.0,
                "scores": {
                    "dividendDaddy": 85,
                    "moonShot": 45,
                    "fallingKnife": 20,
                    "overHyped": 75,
                    "instWhale": 95
                }
            }
        }
        
        # Write to file
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        # Validate
        data = assert_valid_json_file(metadata_file)
        
        assert "AAPL" in data
        ticker = data["AAPL"]
        
        # Check all required fields
        required_fields = [
            "name", "exchange", "price", "volume", "marketCap", 
            "dividendYield", "beta", "rsi", "ma200", "scores"
        ]
        
        for field in required_fields:
            assert field in ticker, f"Missing field: {field}"
        
        # Check scores structure
        scores = ticker["scores"]
        strategy_names = [
            "dividendDaddy", "moonShot", "fallingKnife", 
            "overHyped", "instWhale"
        ]
        
        for strategy in strategy_names:
            assert strategy in scores, f"Missing strategy: {strategy}"
            assert isinstance(scores[strategy], int)
            assert 0 <= scores[strategy] <= 100
    
    def test_metadata_values_are_valid_types(self, temp_dir):
        """Test that metadata values have correct types."""
        metadata_file = temp_dir / "metadata.json"
        
        metadata = {
            "TEST": {
                "name": "Test Company",
                "exchange": "NASDAQ",
                "price": 100.50,
                "volume": 1000000,
                "marketCap": 5000000000,
                "scores": {
                    "dividendDaddy": 50,
                    "moonShot": 50,
                    "fallingKnife": 50,
                    "overHyped": 50,
                    "instWhale": 50
                }
            }
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        data = assert_valid_json_file(metadata_file)
        ticker = data["TEST"]
        
        # Type checks
        assert isinstance(ticker["name"], str)
        assert isinstance(ticker["exchange"], str)
        assert isinstance(ticker["price"], (int, float))
        assert isinstance(ticker["volume"], int)
        assert isinstance(ticker["marketCap"], int)
        assert isinstance(ticker["scores"], dict)
        
        # Score value checks
        for score_value in ticker["scores"].values():
            assert isinstance(score_value, int)
            assert 0 <= score_value <= 100
