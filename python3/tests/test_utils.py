"""
Tests for utility functions.
"""
import pytest
from stock_ticker.utils import get_today, is_valid_symbol


def test_get_today():
    """Test today's date retrieval."""
    today = get_today()
    assert isinstance(today, str)
    assert len(today) == 10  # YYYY-MM-DD format
    assert today.count('-') == 2


def test_is_valid_symbol():
    """Test symbol validation."""
    assert is_valid_symbol('AAPL') is True
    assert is_valid_symbol('MSFT') is True
    assert is_valid_symbol('^VIX') is False
    assert is_valid_symbol('.DJI') is False
    assert is_valid_symbol('') is False
    assert is_valid_symbol('AVERYLONGSYMBOL') is False
