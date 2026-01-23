"""
Utility functions for the stock ticker CLI.
"""
import socket
from datetime import date
from .retry import get_request_metrics


def get_today():
    """Return today's date as ISO string."""
    return date.today().isoformat()


def is_valid_symbol(symbol):
    """
    Check if a symbol is valid for processing.
    
    Rules:
    - Must be 1-5 uppercase letters only
    - No dots, dollars, or special characters
    - Filters out obvious derivatives (but allows legitimate tickers)
    
    Note: This is a permissive filter. The main filtering happens
    in FTP sync using the Test Issue, ETF, and Financial Status columns.
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Remove any whitespace
    symbol = symbol.strip()
    
    # Must be 1-5 uppercase letters only (extended to 5 for some valid tickers)
    # This automatically filters out:
    # - $ prefixes
    # - . dots
    # - Special characters
    import re
    if not re.match(r'^[A-Z]{1,5}$', symbol):
        return False
    
    # Reject obvious test tickers
    if symbol in ('TEST', 'ZZZZ', 'XXXX'):
        return False
    
    # Additional heuristic: If 5 letters and ends in W/R/U/P/Q/F, likely a derivative
    # W = Warrant, R = Right, U = Unit, P = Preferred
    # Q = Bankrupt/Deficient, F = Foreign/ADR
    # Examples: AACBU (Unit), ADSEW (Warrant), BKHAR (Right), AIRTP (Preferred)
    if len(symbol) == 5 and symbol[-1] in ('W', 'R', 'U', 'P', 'Q', 'F'):
        return False
    
    return True


def check_ftp_server(host, timeout=5):
    """Check if FTP server is reachable."""
    metrics = get_request_metrics()
    metrics.record_request('nasdaq_ftp', 'healthcheck')
    
    try:
        socket.create_connection((host, 21), timeout=timeout)
        return True
    except (socket.timeout, socket.error):
        return False


def check_yahoo_finance(host, timeout=5):
    """Check if Yahoo Finance API is reachable."""
    metrics = get_request_metrics()
    metrics.record_request('yahoo_finance', 'healthcheck')
    
    try:
        socket.create_connection((host, 443), timeout=timeout)
        return True
    except (socket.timeout, socket.error):
        return False
