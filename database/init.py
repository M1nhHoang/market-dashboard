"""
Database Initialization and Utilities

Functions for initializing and managing the SQLite database.
"""
import sqlite3
from pathlib import Path
from typing import Optional

from loguru import logger

from .schema import FULL_SCHEMA


def init_database(db_path: Path) -> None:
    """
    Initialize the SQLite database with schema.
    
    Args:
        db_path: Path to the SQLite database file
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Initializing database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(FULL_SCHEMA)
        conn.commit()
        logger.info("Database schema created successfully")
    except Exception as e:
        logger.error(f"Failed to create database schema: {e}")
        raise
    finally:
        conn.close()


def get_connection(db_path: Path) -> sqlite3.Connection:
    """
    Get a database connection with row factory.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        SQLite connection with Row factory
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def check_database_exists(db_path: Path) -> bool:
    """Check if database file exists."""
    return db_path.exists()


def get_table_counts(db_path: Path) -> dict:
    """
    Get row counts for all tables.
    
    Returns:
        Dict with table names and row counts
    """
    conn = get_connection(db_path)
    try:
        tables = [
            'indicators', 'indicator_history', 'events', 'causal_analyses',
            'investigations', 'investigation_evidence', 'topic_frequency',
            'predictions', 'run_history', 'calendar_events', 'score_history'
        ]
        counts = {}
        for table in tables:
            try:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = 0
        return counts
    finally:
        conn.close()


def vacuum_database(db_path: Path) -> None:
    """Vacuum database to reclaim space."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("VACUUM")
        logger.info("Database vacuumed successfully")
    finally:
        conn.close()
