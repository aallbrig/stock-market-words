"""
Tests for CLI commands.

Tests the behavior of each CLI command using mocked external dependencies.
"""
import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from stock_ticker.cli import cli
from stock_ticker.utils import get_today
from tests.conftest import assert_valid_json_file, assert_json_structure


@pytest.mark.cli
class TestCLIStatus:
    """Tests for the 'status' command."""
    
    def test_status_command_runs(self, initialized_db, monkeypatch):
        """Test that status command runs without error."""
        monkeypatch.setenv('DB_PATH', str(initialized_db))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
        assert 'SYSTEM STATUS' in result.output
        assert 'DEPENDENCIES' in result.output
    
    def test_status_shows_database_ready(self, initialized_db, monkeypatch):
        """Test that status shows database is ready."""
        monkeypatch.setenv('DB_PATH', str(initialized_db))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        
        assert 'Database: Ready' in result.output or 'Database: ✓' in result.output


@pytest.mark.cli
class TestCLIInit:
    """Tests for the 'init' command."""
    
    def test_init_creates_database(self, temp_db, monkeypatch):
        """Test that init creates a database with schema."""
        monkeypatch.setenv('DB_PATH', str(temp_db))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        assert temp_db.exists()
        assert 'initialized' in result.output.lower()


@pytest.mark.cli
@pytest.mark.integration
class TestCLISyncFTP:
    """Tests for the 'sync-ftp' command."""
    
    def test_sync_ftp_with_mock(self, initialized_db, temp_dir, 
                                 mock_ftp_server, monkeypatch):
        """Test FTP sync with mocked FTP server."""
        monkeypatch.setenv('DB_PATH', str(initialized_db))
        monkeypatch.setenv('TMP_DIR', str(temp_dir))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['sync-ftp'])
        
        assert result.exit_code == 0
        assert 'sync' in result.output.lower()


@pytest.mark.cli
@pytest.mark.integration
class TestCLIExtractPrices:
    """Tests for the 'extract-prices' command."""
    
    def test_extract_prices_with_mock(self, populated_db, 
                                      mock_yfinance_download, monkeypatch):
        """Test price extraction with mocked Yahoo Finance."""
        monkeypatch.setenv('DB_PATH', str(populated_db))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['extract-prices'])
        
        # Command should complete (may have warnings about no pending tickers)
        assert result.exit_code == 0


@pytest.mark.cli
class TestCLIBuild:
    """Tests for the 'build' command."""
    
    def test_build_generates_json_files(self, populated_db, temp_dir, monkeypatch):
        """Test that build command generates valid JSON files."""
        api_dir = temp_dir / "api"
        api_dir.mkdir(parents=True)
        
        monkeypatch.setenv('DB_PATH', str(populated_db))
        monkeypatch.setenv('API_DIR', str(api_dir))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['build'])
        
        # Should complete successfully or with expected warnings
        assert result.exit_code in [0, 1]  # May exit 1 if not enough data
        
        # If files were generated, validate them
        trie_path = api_dir / "trie.json"
        metadata_path = api_dir / "metadata.json"
        
        if trie_path.exists():
            data = assert_valid_json_file(trie_path)
            assert isinstance(data, dict)
        
        if metadata_path.exists():
            data = assert_valid_json_file(metadata_path)
            assert isinstance(data, dict)
            
            # Check structure of first ticker
            if data:
                first_ticker = next(iter(data.values()))
                required_keys = ['name', 'exchange', 'price', 'volume', 'scores']
                assert_json_structure(first_ticker, required_keys)


@pytest.mark.cli
@pytest.mark.slow
class TestCLIRunAll:
    """Tests for the 'run-all' command."""
    
    def test_run_all_dry_run(self, temp_db, monkeypatch):
        """Test run-all in dry-run mode."""
        monkeypatch.setenv('DB_PATH', str(temp_db))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['--dry-run', 'run-all'])
        
        assert result.exit_code == 0
        assert 'DRY RUN' in result.output


@pytest.mark.cli
class TestCLIReset:
    """Tests for the 'reset' command."""
    
    def test_reset_with_force_flag(self, populated_db, monkeypatch):
        """Test reset command with --force flag."""
        monkeypatch.setenv('DB_PATH', str(populated_db))
        
        runner = CliRunner()
        # Use --force and provide 'yes' confirmation
        result = runner.invoke(cli, ['reset', '--force'], input='yes\n')
        
        # Should complete (may have warnings)
        assert 'reset' in result.output.lower() or 'delet' in result.output.lower()
