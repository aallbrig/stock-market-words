"""
SQLite database backup utility.

Provides functions to create timestamped SQL dumps of the market data database.
Used by both the CLI and migration system.
"""

import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime


def get_backup_dir(base_path="data"):
    """
    Ensure backup directory exists and return its path.
    
    Args:
        base_path (str): Base directory where backups folder will be created
        
    Returns:
        Path: Path object pointing to the backup directory
    """
    backup_dir = Path(base_path) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_backup(db_path="data/market_data.db", backup_dir=None):
    """
    Create a timestamped SQL dump of the database.
    
    Args:
        db_path (str): Path to the SQLite database file
        backup_dir (Path, optional): Directory to store backup. 
                                     If None, uses get_backup_dir()
        
    Returns:
        str: Path to the created backup file
        
    Raises:
        FileNotFoundError: If database file doesn't exist
        sqlite3.Error: If backup creation fails
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    if backup_dir is None:
        backup_dir = get_backup_dir()
    
    # Generate timestamp in UTC
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"market_data_{timestamp}.sql"
    
    # Connect to database and dump to SQL file
    conn = sqlite3.connect(db_path)
    try:
        with open(backup_file, 'w') as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
    finally:
        conn.close()
    
    return str(backup_file)
