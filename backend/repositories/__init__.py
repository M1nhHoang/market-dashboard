"""
SQLAlchemy-based Repositories

This package provides async repository pattern using SQLAlchemy ORM.

Usage:
    from repositories import IndicatorRepository
    from database import get_session
    
    async with get_session() as session:
        repo = IndicatorRepository(session)
        indicator = await repo.get("interbank_on")
        all_indicators = await repo.get_all()
"""

from .base import BaseRepository
from .indicators import IndicatorRepository
from .events import EventRepository
from .insights import SignalRepository, ThemeRepository, WatchlistRepository, SignalAccuracyStatsRepository
from .run_history import RunHistoryRepository
from .llm_history import LLMHistoryRepository

__all__ = [
    "BaseRepository",
    "IndicatorRepository",
    "EventRepository",
    # Insights (Signals, Themes, Watchlist)
    "SignalRepository",
    "ThemeRepository",
    "WatchlistRepository",
    "SignalAccuracyStatsRepository",
    # System
    "RunHistoryRepository",
    "LLMHistoryRepository",
]
