# Python CLI Tests

Comprehensive test suite for the stock-ticker CLI tool.

## Overview

This test suite provides:
- **Unit tests** - Fast tests for individual functions
- **Integration tests** - Tests with database and file I/O
- **CLI tests** - Tests for command-line interface behavior
- **Mock tests** - Tests using mocked external APIs (Yahoo Finance, FTP)
- **JSON validation** - Tests to ensure generated JSON files are valid

## Running Tests

### All Tests

```bash
cd python3
pytest
```

### By Category

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# CLI command tests
pytest -m cli

# Database tests
pytest -m database

# API mock tests
pytest -m api
```

### With Coverage

```bash
pytest --cov=src/stock_ticker --cov-report=html
```

View coverage report: `open coverage_html/index.html`

### Verbose Output

```bash
pytest -v
```

### Run Specific Test File

```bash
pytest tests/test_database.py
pytest tests/test_cli.py
pytest tests/test_hugo_generators.py
```

### Run Specific Test

```bash
pytest tests/test_database.py::TestDatabaseInitialization::test_init_db_creates_tables
```

## Test Structure

```
tests/
├── conftest.py              # Fixtures and test utilities
├── test_database.py         # Database operations
├── test_cli.py              # CLI commands
├── test_extractors.py       # Data extraction (Yahoo Finance)
├── test_builders.py         # Strategy scoring and JSON building
├── test_hugo_generators.py  # Hugo content generation
└── test_utils.py            # Utility functions
```

## Fixtures

Common fixtures available in all tests (from `conftest.py`):

### Temporary Resources

- `temp_dir` - Temporary directory (auto-cleaned)
- `temp_db` - Temporary SQLite database file
- `initialized_db` - Database with schema initialized
- `populated_db` - Database with sample data
- `temp_hugo_dir` - Temporary Hugo-like directory structure

### Sample Data

- `sample_tickers` - List of sample ticker dictionaries
- `sample_daily_metrics` - List of sample metrics dictionaries
- `sample_strategy_scores` - List of sample strategy scores

### Mocks

- `mock_yfinance_ticker` - Mocked yfinance.Ticker class
- `mock_yfinance_download` - Mocked yfinance.download function
- `mock_ftp_server` - Mocked FTP server

### Utilities

- `assert_valid_json_file(filepath)` - Assert file contains valid JSON
- `assert_json_structure(data, keys)` - Assert JSON has required keys

## Test Markers

Tests are marked for easy filtering:

```python
@pytest.mark.unit         # Unit tests (fast, no dependencies)
@pytest.mark.integration  # Integration tests (database, files)
@pytest.mark.cli          # CLI command tests
@pytest.mark.database     # Database-related tests
@pytest.mark.api          # Tests with mocked APIs
@pytest.mark.slow         # Slow-running tests
```

## What Gets Tested

### Database Module
- ✅ Schema initialization
- ✅ Table creation
- ✅ Data insertion and queries
- ✅ Pipeline state tracking
- ✅ Step recommendations

### CLI Commands
- ✅ `status` - Shows system status
- ✅ `init` - Initializes database
- ✅ `sync-ftp` - Syncs ticker lists (mocked FTP)
- ✅ `extract-prices` - Extracts prices (mocked Yahoo Finance)
- ✅ `extract-metadata` - Extracts metadata (mocked Yahoo Finance)
- ✅ `build` - Builds JSON assets
- ✅ `reset` - Resets data
- ✅ `run-all` - Full pipeline (dry-run mode)

### Data Extraction
- ✅ Price/volume extraction with mocked API
- ✅ Metadata extraction with mocked API
- ✅ Batch processing logic
- ✅ Error handling for missing data
- ✅ Data validation (price, volume, RSI ranges)

### Builders & Scoring
- ✅ Strategy score calculations
- ✅ Trie generation for autocomplete
- ✅ Metadata JSON generation
- ✅ JSON file validation

### Hugo Generators
- ✅ Raw FTP data export
- ✅ Filtered data export
- ✅ Strategy filter generation
- ✅ JSON structure validation

### JSON Validation
- ✅ Valid JSON format
- ✅ Required fields present
- ✅ Correct data types
- ✅ Score ranges (0-100)
- ✅ Nested structure validation

## Mocking External Dependencies

### Yahoo Finance API

Tests use `pytest-mock` to mock Yahoo Finance calls:

```python
def test_with_mock_yahoo(mock_yfinance_download):
    # mock_yfinance_download is automatically available
    # Returns sample data instead of hitting real API
    extract_prices()
    
    assert mock_yfinance_download.called
```

### FTP Server

FTP connections are mocked to return sample NASDAQ data:

```python
def test_with_mock_ftp(mock_ftp_server):
    # mock_ftp_server provides sample nasdaqlisted.txt data
    sync_ftp()
    
    assert mock_ftp_server.called
```

### Database

Tests use temporary SQLite databases that are cleaned up automatically:

```python
def test_with_temp_db(initialized_db):
    # initialized_db is a real SQLite database in /tmp
    # Automatically deleted after test
    conn = sqlite3.connect(initialized_db)
    # ... use database
```

## Example Test

```python
import pytest
from tests.conftest import assert_valid_json_file

@pytest.mark.integration
def test_build_creates_valid_json(populated_db, temp_dir):
    """Test that build command creates valid JSON."""
    api_dir = temp_dir / "api"
    api_dir.mkdir()
    
    # Run build
    build_assets(db_path=populated_db, output_dir=api_dir)
    
    # Validate JSON
    metadata_file = api_dir / "metadata.json"
    if metadata_file.exists():
        data = assert_valid_json_file(metadata_file)
        assert isinstance(data, dict)
        assert len(data) > 0
```

## Continuous Integration

Tests run automatically in GitHub Actions on every push/PR.

See `.github/workflows/` for CI configuration.

## Writing New Tests

### 1. Choose the Right Test File

- Database operations → `test_database.py`
- CLI commands → `test_cli.py`
- Data extraction → `test_extractors.py`
- Strategy scoring → `test_builders.py`
- Hugo generation → `test_hugo_generators.py`
- Utility functions → `test_utils.py`

### 2. Use Appropriate Fixtures

```python
def test_my_feature(initialized_db, sample_tickers, mock_yfinance_download):
    # Fixtures are injected automatically
    pass
```

### 3. Mark Your Test

```python
@pytest.mark.unit
def test_fast_unit_test():
    pass

@pytest.mark.integration
@pytest.mark.database
def test_database_operation():
    pass
```

### 4. Validate JSON Output

```python
from tests.conftest import assert_valid_json_file, assert_json_structure

data = assert_valid_json_file(json_file)
assert_json_structure(data, ['required', 'keys'])
```

## Troubleshooting

### Tests Fail Due to Missing Dependencies

```bash
pip install -r requirements.txt
```

### Coverage Report Not Generated

```bash
pip install pytest-cov
pytest --cov
```

### Import Errors

Make sure you're running from the `python3/` directory:

```bash
cd python3
pytest
```

### Mock Not Working

Ensure `pytest-mock` is installed:

```bash
pip install pytest-mock
```

## Performance

- **Unit tests**: < 1 second
- **Integration tests**: 2-5 seconds
- **Full suite**: 5-10 seconds

Tests are designed to be fast by:
- Using temporary in-memory databases where possible
- Mocking all external API calls
- Using small sample datasets
- Cleaning up resources automatically

## Benefits

✅ **No API Rate Limits** - Mocked APIs don't hit real services  
✅ **Fast Execution** - Tests run in seconds, not minutes  
✅ **Reproducible** - Same mocked data every time  
✅ **Safe** - No accidental API charges or rate limit bans  
✅ **Comprehensive** - Tests cover all major code paths  
✅ **JSON Validation** - Ensures generated files are valid  
✅ **Confidence** - Make changes without breaking things
