"""
Database configuration and common utilities.
This module provides database connection management and shared functionality
for all database models.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent


def get_db_connection(db_name: str) -> sqlite3.Connection:
    """
    Get a database connection for the specified database name.

    Args:
        db_name: Name of the database file (e.g., 'user.db')

    Returns:
        sqlite3.Connection: Database connection object
    """
    db_file = DB_PATH / db_name
    return sqlite3.connect(str(db_file))
