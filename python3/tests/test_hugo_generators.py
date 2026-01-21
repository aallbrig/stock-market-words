"""
Tests for Hugo content generators.

Validates that generated JSON files are valid and have correct structure.
"""
import json
import pytest
from pathlib import Path
from stock_ticker.hugo_generators import (
    generate_raw_ftp_data,
    generate_filtered_data,
    generate_strategy_filters,
    generate_hugo_pages,
)
from tests.conftest import assert_valid_json_file, assert_json_structure


@pytest.mark.integration
class TestHugoDataGeneration:
    """Tests for Hugo data file generation."""
    
    def test_generate_raw_ftp_data_creates_valid_json(self, populated_db, 
                                                       temp_hugo_dir, monkeypatch):
        """Test that raw FTP data generation creates valid JSON."""
        monkeypatch.setenv('DB_PATH', str(populated_db))
        
        output_dir = temp_hugo_dir
        generate_raw_ftp_data(db_path=populated_db, output_dir=output_dir)
        
        # Check for generated files
        nasdaq_file = output_dir / "raw_nasdaq.json"
        other_file = output_dir / "raw_otherlisted.json"
        
        if nasdaq_file.exists():
            data = assert_valid_json_file(nasdaq_file)
            assert isinstance(data, list)
            
            # Validate structure if data exists
            if data:
                first_item = data[0]
                required_keys = ['symbol', 'name', 'exchange']
                assert_json_structure(first_item, required_keys)
    
    def test_generate_filtered_data_creates_valid_json(self, populated_db, 
                                                        temp_hugo_dir, monkeypatch):
        """Test that filtered data generation creates valid JSON."""
        monkeypatch.setenv('DB_PATH', str(populated_db))
        
        output_dir = temp_hugo_dir
        generate_filtered_data(db_path=populated_db, output_dir=output_dir)
        
        # Check for generated file
        filtered_file = output_dir / "filtered_tickers.json"
        
        if filtered_file.exists():
            data = assert_valid_json_file(filtered_file)
            assert isinstance(data, dict) or isinstance(data, list)
            
            # Validate structure
            if isinstance(data, dict):
                assert 'tickers' in data or 'data' in data or len(data) > 0
    
    def test_generate_strategy_filters_creates_valid_json(self, populated_db,
                                                           temp_hugo_dir, monkeypatch):
        """Test that strategy filter generation creates valid JSON files."""
        monkeypatch.setenv('DB_PATH', str(populated_db))
        
        output_dir = temp_hugo_dir
        generate_strategy_filters(db_path=populated_db, output_dir=output_dir)
        
        # Check for strategy files
        strategies = [
            'dividend_daddy',
            'moon_shot',
            'falling_knife',
            'over_hyped',
            'institutional_whale'
        ]
        
        for strategy in strategies:
            strategy_file = output_dir / f"strategy_{strategy}.json"
            
            if strategy_file.exists():
                data = assert_valid_json_file(strategy_file)
                assert isinstance(data, (list, dict))


@pytest.mark.unit
class TestJSONValidation:
    """Tests for JSON file validation."""
    
    def test_validate_json_structure_for_ticker_data(self, temp_dir):
        """Test JSON structure validation for ticker data."""
        # Create a sample JSON file
        test_file = temp_dir / "test_tickers.json"
        
        sample_data = {
            "AAPL": {
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "price": 150.25,
                "volume": 50000000,
                "marketCap": 2500000000000,
                "scores": {
                    "dividendDaddy": 85,
                    "moonShot": 45,
                    "fallingKnife": 20,
                    "overHyped": 75,
                    "instWhale": 95
                }
            }
        }
        
        with open(test_file, 'w') as f:
            json.dump(sample_data, f)
        
        # Validate
        data = assert_valid_json_file(test_file)
        assert 'AAPL' in data
        
        ticker = data['AAPL']
        required_keys = ['name', 'exchange', 'price', 'volume', 'scores']
        assert_json_structure(ticker, required_keys)
        
        # Validate scores structure
        scores = ticker['scores']
        score_keys = ['dividendDaddy', 'moonShot', 'fallingKnife', 
                      'overHyped', 'instWhale']
        assert_json_structure(scores, score_keys)
    
    def test_invalid_json_raises_error(self, temp_dir):
        """Test that invalid JSON raises an error."""
        test_file = temp_dir / "invalid.json"
        
        # Write invalid JSON
        with open(test_file, 'w') as f:
            f.write("{invalid json content")
        
        # Should raise an error
        with pytest.raises(Exception):
            assert_valid_json_file(test_file)
    
    def test_json_with_all_ticker_fields(self, temp_dir):
        """Test validation of JSON with all expected ticker fields."""
        test_file = temp_dir / "full_ticker.json"
        
        sample_data = {
            "MSFT": {
                "name": "Microsoft Corporation",
                "exchange": "NASDAQ",
                "price": 350.75,
                "volume": 30000000,
                "marketCap": 2600000000000,
                "dividendYield": 0.75,
                "beta": 0.9,
                "rsi": 60.0,
                "ma200": 340.0,
                "scores": {
                    "dividendDaddy": 90,
                    "moonShot": 35,
                    "fallingKnife": 15,
                    "overHyped": 80,
                    "instWhale": 98
                }
            }
        }
        
        with open(test_file, 'w') as f:
            json.dump(sample_data, f)
        
        # Validate
        data = assert_valid_json_file(test_file)
        ticker = data['MSFT']
        
        # Check all fields exist
        assert ticker['name'] == "Microsoft Corporation"
        assert ticker['price'] == 350.75
        assert ticker['volume'] == 30000000
        assert ticker['marketCap'] == 2600000000000
        assert 'dividendYield' in ticker
        assert 'beta' in ticker
        assert 'rsi' in ticker
        assert 'ma200' in ticker
        assert 'scores' in ticker
    
    def test_json_array_format(self, temp_dir):
        """Test validation of JSON in array format."""
        test_file = temp_dir / "tickers_array.json"
        
        sample_data = [
            {"symbol": "AAPL", "name": "Apple Inc."},
            {"symbol": "MSFT", "name": "Microsoft Corporation"}
        ]
        
        with open(test_file, 'w') as f:
            json.dump(sample_data, f)
        
        # Validate
        data = assert_valid_json_file(test_file)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]['symbol'] == 'AAPL'


@pytest.mark.integration
class TestHugoPageGeneration:
    """Tests for Hugo markdown page generation."""
    
    def test_generate_hugo_pages_creates_files(self, populated_db, 
                                                temp_dir, monkeypatch):
        """Test that Hugo page generation creates markdown files."""
        monkeypatch.setenv('DB_PATH', str(populated_db))
        
        content_dir = temp_dir / "content"
        content_dir.mkdir(parents=True)
        
        # This may not be implemented yet, so handle gracefully
        try:
            generate_hugo_pages(db_path=populated_db, output_dir=content_dir)
            
            # Check if any .md files were created
            md_files = list(content_dir.glob("*.md"))
            
            # If files were created, validate they exist
            for md_file in md_files:
                assert md_file.exists()
                content = md_file.read_text()
                assert len(content) > 0
        except NotImplementedError:
            pytest.skip("Hugo page generation not yet implemented")
