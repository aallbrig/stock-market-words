"""
Tests for the database module.
"""
import sqlite3
import pytest
from pathlib import Path
from stock_ticker.database import (
    get_connection,
    init_db,
    ensure_initialized,
    get_pipeline_state,
    recommend_next_step
)
from stock_ticker.utils import get_today


@pytest.mark.database
class TestDatabaseInitialization:
    """Tests for database initialization."""
    
    def test_init_db_creates_tables(self, temp_db):
        """Test that init_db creates all required tables."""
        init_db(db_path=temp_db)
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Check that tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'tickers',
            'daily_metrics',
            'strategy_scores',
            'pipeline_steps',
            'sync_history'
        ]
        
        for table in required_tables:
            assert table in tables, f"Table '{table}' was not created"
        
        conn.close()
    
    def test_ensure_initialized_creates_db_if_missing(self, temp_db):
        """Test that ensure_initialized creates database if it doesn't exist."""
        assert not temp_db.exists()
        
        ensure_initialized(db_path=temp_db)
        
        assert temp_db.exists()
        
        # Verify tables exist
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert len(tables) > 0
        conn.close()


@pytest.mark.database
class TestDatabaseOperations:
    """Tests for database operations."""
    
    def test_insert_ticker(self, initialized_db):
        """Test inserting a ticker into the database."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tickers (symbol, name, exchange, is_etf)
            VALUES (?, ?, ?, ?)
        """, ('TEST', 'Test Company', 'NASDAQ', False))
        
        conn.commit()
        
        # Verify insertion
        cursor.execute("SELECT * FROM tickers WHERE symbol = 'TEST'")
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] == 'TEST'
        assert result[1] == 'Test Company'
        
        conn.close()
    
    def test_insert_daily_metrics(self, initialized_db):
        """Test inserting daily metrics."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        today = get_today()
        
        # First insert a ticker
        cursor.execute("""
            INSERT INTO tickers (symbol, name, exchange, is_etf)
            VALUES (?, ?, ?, ?)
        """, ('TEST', 'Test Company', 'NASDAQ', False))
        
        # Insert metrics
        cursor.execute("""
            INSERT INTO daily_metrics 
            (symbol, date, price, volume, market_cap)
            VALUES (?, ?, ?, ?, ?)
        """, ('TEST', today, 100.50, 1000000, 5000000000))
        
        conn.commit()
        
        # Verify insertion
        cursor.execute("""
            SELECT * FROM daily_metrics 
            WHERE symbol = 'TEST' AND date = ?
        """, (today,))
        result = cursor.fetchone()
        
        assert result is not None
        assert result[2] == 100.50  # price
        assert result[3] == 1000000  # volume
        
        conn.close()


@pytest.mark.database
class TestPipelineState:
    """Tests for pipeline state management."""
    
    def test_get_pipeline_state_empty_db(self, initialized_db):
        """Test pipeline state with empty database."""
        state = get_pipeline_state(db_path=initialized_db)
        
        assert state['status'] == 'idle'
        assert state['current_step'] is None
        assert len(state['completed_steps']) == 0
    
    def test_recommend_next_step_empty_db(self, initialized_db):
        """Test next step recommendation with empty database."""
        step, reason = recommend_next_step(db_path=initialized_db)
        
        assert step == 'sync-ftp'
        assert 'download' in reason.lower() or 'sync' in reason.lower()
    
    def test_pipeline_step_tracking(self, initialized_db):
        """Test that pipeline steps are tracked correctly."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        today = get_today()
        
        # Record a step completion
        cursor.execute("""
            INSERT INTO pipeline_steps 
            (step_name, run_date, tickers_processed, status)
            VALUES (?, ?, ?, ?)
        """, ('sync-ftp', today, 100, 'completed'))
        
        conn.commit()
        conn.close()
        
        # Check pipeline state
        state = get_pipeline_state(db_path=initialized_db)
        
        assert 'sync-ftp' in state['completed_steps']


@pytest.mark.database
class TestDatabaseQueries:
    """Tests for common database queries."""
    
    def test_query_tickers_by_exchange(self, populated_db):
        """Test querying tickers by exchange."""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol FROM tickers 
            WHERE exchange = 'NASDAQ'
            ORDER BY symbol
        """)
        results = [row[0] for row in cursor.fetchall()]
        
        assert 'AAPL' in results
        assert 'MSFT' in results
        assert 'TSLA' in results
        
        conn.close()
    
    def test_filter_etfs(self, populated_db):
        """Test filtering out ETFs."""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol FROM tickers 
            WHERE is_etf = 0
        """)
        results = [row[0] for row in cursor.fetchall()]
        
        assert 'SPY' not in results
        assert 'AAPL' in results
        
        conn.close()
    
    def test_query_with_metrics(self, populated_db):
        """Test querying tickers with metrics."""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        today = get_today()
        
        cursor.execute("""
            SELECT t.symbol, dm.price, dm.volume
            FROM tickers t
            JOIN daily_metrics dm ON t.symbol = dm.symbol
            WHERE dm.date = ? AND dm.price >= 100
            ORDER BY t.symbol
        """, (today,))
        
        results = cursor.fetchall()
        
        assert len(results) == 2
        assert results[0][0] in ['AAPL', 'MSFT']
        
        conn.close()

