"""
Database Module - Market Intelligence Dashboard

This module provides database access for the Market Intelligence system.

Structure:
    database/
    ├── __init__.py      # This file - public API
    ├── schema.py        # SQL schema definitions
    └── init.py          # Database initialization utilities

Usage:
    # Use DAO layer for all database operations
    from dao import get_db
    
    db = get_db()
    indicator = db.indicators.get("interbank_on")
    event_id = db.events.create(event_data)
    
    # Or use raw connection for direct SQL
    from database import get_connection, init_database
    
    init_database(db_path)
    conn = get_connection(db_path)

For schema details, see database/schema.py
"""

# Schema exports
from .schema import (
    FULL_SCHEMA,
    INDICATORS_SCHEMA,
    EVENTS_SCHEMA,
    INVESTIGATIONS_SCHEMA,
    SYSTEM_SCHEMA,
)

# Initialization utilities
from .init import (
    init_database,
    get_connection,
    check_database_exists,
    get_table_counts,
    vacuum_database,
)

# Re-export DAO for convenience
from dao import get_db, DatabaseConnection

# Re-export constants for backward compatibility
from constants import (
    INDICATOR_GROUPS,
    INTERBANK_TERM_MAP,
    EVENT_CATEGORIES,
)

__all__ = [
    # Schema
    "FULL_SCHEMA",
    "INDICATORS_SCHEMA", 
    "EVENTS_SCHEMA",
    "INVESTIGATIONS_SCHEMA",
    "SYSTEM_SCHEMA",
    # Init utilities
    "init_database",
    "get_connection",
    "check_database_exists",
    "get_table_counts",
    "vacuum_database",
    # DAO
    "get_db",
    "DatabaseConnection",
    # Constants (backward compat)
    "INDICATOR_GROUPS",
    "INTERBANK_TERM_MAP",
    "EVENT_CATEGORIES",
]
