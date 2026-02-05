"""
Database Access Object (DAO) Package

Provides a clean abstraction layer for database operations.
Uses Repository pattern to separate data access logic from business logic.

Usage:
    from dao import get_db, IndicatorRepository, EventRepository

    db = get_db()
    
    # Get indicator
    indicator = db.indicators.get("interbank_on")
    
    # Save event
    event_id = db.events.create(event_data)
"""

from .connection import DatabaseConnection, get_db
from .base import BaseRepository

# Entities
from .entities import (
    Entity,
    Indicator,
    IndicatorHistory,
    Event,
    CausalAnalysis,
    TopicFrequency,
    Investigation,
    InvestigationEvidence,
    Prediction,
    RunHistory,
    CalendarEvent,
)

# Repositories
from .indicators import IndicatorRepository
from .events import EventRepository
from .investigations import InvestigationRepository
from .run_history import RunHistoryRepository


__all__ = [
    # Connection
    "DatabaseConnection",
    "get_db",
    "BaseRepository",
    # Entities
    "Entity",
    "Indicator",
    "IndicatorHistory",
    "Event",
    "CausalAnalysis",
    "TopicFrequency",
    "Investigation",
    "InvestigationEvidence",
    "Prediction",
    "RunHistory",
    "CalendarEvent",
    # Repositories
    "IndicatorRepository",
    "EventRepository",
    "InvestigationRepository",
    "RunHistoryRepository",
]
