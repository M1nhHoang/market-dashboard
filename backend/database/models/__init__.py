"""
SQLAlchemy ORM Models

This module defines all database models using SQLAlchemy ORM.
Models are organized by domain:
- Indicators: Market indicators and their history
- Events: News events and causal analysis
- Insights: Signals, Themes, and Watchlist for predictions and tracking
- System: Run history, calendar, LLM history, etc.
"""

from .base import Base, TimestampMixin
from .indicators import Indicator, IndicatorHistory
from .events import Event, CausalAnalysis, TopicFrequency, ScoreHistory
from .insights import Signal, Theme, Watchlist, SignalAccuracyStats
from .system import RunHistory, CalendarEvent
from .llm_history import LLMCallHistory

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Indicators
    "Indicator",
    "IndicatorHistory",
    # Events
    "Event",
    "CausalAnalysis",
    "TopicFrequency",
    "ScoreHistory",
    # Insights (Signals, Themes, Watchlist)
    "Signal",
    "Theme",
    "Watchlist",
    "SignalAccuracyStats",
    # System
    "RunHistory",
    "CalendarEvent",
    # LLM
    "LLMCallHistory",
]
