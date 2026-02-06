"""
Database Module - Market Intelligence Dashboard

This module provides database access for the Market Intelligence system.

Structure:
    database/
    ├── __init__.py      # This file - public API
    ├── session.py       # SQLAlchemy async session management
    ├── init.py          # Database initialization utilities
    └── models/          # SQLAlchemy ORM models
        ├── __init__.py
        ├── base.py
        ├── indicators.py
        ├── events.py
        ├── investigations.py
        └── system.py

Usage:
    from database import get_session
    from database.models import Indicator, Event
    
    async with get_session() as session:
        result = await session.execute(select(Indicator))
        indicators = result.scalars().all()

For schema details, see database/models/
"""

# SQLAlchemy Models
from .models import (
    # Base
    Base,
    TimestampMixin,
    # Indicators
    Indicator,
    IndicatorHistory,
    # Events
    Event,
    CausalAnalysis,
    TopicFrequency,
    ScoreHistory,
    # Investigations
    Investigation,
    InvestigationEvidence,
    Prediction,
    # System
    RunHistory,
    CalendarEvent,
)

# Session Management
from .session import (
    init_engine,
    close_engine,
    create_tables,
    drop_tables,
    get_session,
    get_session_dependency,
    get_connection,
)

# Initialization utilities
from .init import (
    init_database,
    init_database_async,
    get_table_counts_async,
    check_database_exists,
    run_migrations,
    create_migration,
)

# Re-export SBV-specific mappings from data_transformers
from data_transformers.sbv import (
    INDICATOR_GROUPS,
    INTERBANK_TERM_MAP,
    EVENT_CATEGORIES,
)

__all__ = [
    # SQLAlchemy Models
    "Base",
    "TimestampMixin",
    "Indicator",
    "IndicatorHistory",
    "Event",
    "CausalAnalysis",
    "TopicFrequency",
    "ScoreHistory",
    "Investigation",
    "InvestigationEvidence",
    "Prediction",
    "RunHistory",
    "CalendarEvent",
    # Session Management
    "init_engine",
    "close_engine",
    "create_tables",
    "drop_tables",
    "get_session",
    "get_session_dependency",
    "get_connection",
    # Init utilities
    "init_database",
    "init_database_async",
    "get_table_counts_async",
    "check_database_exists",
    "run_migrations",
    "create_migration",
    # Constants (re-exported from data_transformers.sbv)
    "INDICATOR_GROUPS",
    "INTERBANK_TERM_MAP",
    "EVENT_CATEGORIES",
]
