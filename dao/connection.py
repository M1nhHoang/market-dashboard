"""
Database Connection Manager

Handles SQLite connections with proper resource management.
Provides both context manager and singleton patterns.
"""
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from loguru import logger

from config import settings


# Global connection instance (singleton pattern)
_connection_instance: Optional["DatabaseConnection"] = None


class DatabaseConnection:
    """
    Database connection manager with lazy initialization.
    
    Provides:
    - Connection pooling (reuse connections)
    - Context managers for transactions
    - Row factory for dict-like access
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize connection manager.
        
        Args:
            db_path: Path to SQLite database. Uses settings.DATABASE_PATH if not provided.
        """
        self.db_path = db_path or settings.DATABASE_PATH
        self._conn: Optional[sqlite3.Connection] = None
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Lazy-loaded repositories
        self._indicators: Optional["IndicatorRepository"] = None
        self._events: Optional["EventRepository"] = None
        self._investigations: Optional["InvestigationRepository"] = None
        self._run_history: Optional["RunHistoryRepository"] = None
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            # Enable foreign keys
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn
    
    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        
        Usage:
            with db.transaction() as conn:
                conn.execute("INSERT INTO ...")
                conn.execute("UPDATE ...")
            # Auto-commits on success, rolls back on exception
        """
        conn = self.connection
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
    
    @contextmanager
    def cursor(self):
        """
        Context manager for database cursor.
        
        Usage:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM ...")
                rows = cur.fetchall()
        """
        conn = self.connection
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor."""
        return self.connection.execute(query, params)
    
    def executemany(self, query: str, params_list: list) -> sqlite3.Cursor:
        """Execute a query with multiple parameter sets."""
        return self.connection.executemany(query, params_list)
    
    def commit(self) -> None:
        """Commit current transaction."""
        self.connection.commit()
    
    def rollback(self) -> None:
        """Rollback current transaction."""
        self.connection.rollback()
    
    # ============================================
    # REPOSITORY ACCESSORS (Lazy-loaded)
    # ============================================
    
    @property
    def indicators(self) -> "IndicatorRepository":
        """Get indicator repository."""
        if self._indicators is None:
            from .indicators import IndicatorRepository
            self._indicators = IndicatorRepository(self)
        return self._indicators
    
    @property
    def events(self) -> "EventRepository":
        """Get event repository."""
        if self._events is None:
            from .events import EventRepository
            self._events = EventRepository(self)
        return self._events
    
    @property
    def investigations(self) -> "InvestigationRepository":
        """Get investigation repository."""
        if self._investigations is None:
            from .investigations import InvestigationRepository
            self._investigations = InvestigationRepository(self)
        return self._investigations
    
    @property
    def run_history(self) -> "RunHistoryRepository":
        """Get run history repository."""
        if self._run_history is None:
            from .run_history import RunHistoryRepository
            self._run_history = RunHistoryRepository(self)
        return self._run_history
    
    def __enter__(self) -> "DatabaseConnection":
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()


def get_db(db_path: Optional[Path] = None) -> DatabaseConnection:
    """
    Get database connection instance (singleton).
    
    Args:
        db_path: Optional path to database file
        
    Returns:
        DatabaseConnection instance
    """
    global _connection_instance
    
    if _connection_instance is None:
        _connection_instance = DatabaseConnection(db_path)
    
    return _connection_instance


def reset_db() -> None:
    """Reset the global database connection (for testing)."""
    global _connection_instance
    
    if _connection_instance:
        _connection_instance.close()
        _connection_instance = None
