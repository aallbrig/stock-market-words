"""
Logging configuration for the stock ticker CLI.
"""
import logging
from .config import ERROR_LOG_PATH


def setup_logging():
    """Configure and return a logger with console and file handlers."""
    logger = logging.getLogger("stock_ticker")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler for errors
    file_handler = logging.FileHandler(ERROR_LOG_PATH)
    file_handler.setLevel(logging.ERROR)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
