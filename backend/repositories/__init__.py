"""
SQLAlchemy-based Repositories

This package provides async repository pattern using SQLAlchemy ORM.
These repositories replace the legacy raw SQL-based DAOs.

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
from .investigations import InvestigationRepository
from .run_history import RunHistoryRepository
from .llm_history import LLMHistoryRepository

__all__ = [
    "BaseRepository",
    "IndicatorRepository",
    "EventRepository",
    "InvestigationRepository",
    "RunHistoryRepository",
    "LLMHistoryRepository",
]
