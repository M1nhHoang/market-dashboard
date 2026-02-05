"""
Run history and calendar event entities.
"""
from dataclasses import dataclass
from typing import Optional

from .base import Entity


@dataclass
class RunHistory(Entity):
    """Run history entity tracking each analysis pipeline run."""
    run_date: str = ""
    run_time: str = ""
    
    # Stats
    news_count: int = 0
    events_extracted: int = 0
    events_key: int = 0
    events_other: int = 0
    investigations_opened: int = 0
    investigations_updated: int = 0
    investigations_resolved: int = 0
    
    # Summary
    summary: Optional[str] = None
    # Status: success, partial, failed
    status: str = "success"


@dataclass
class CalendarEvent(Entity):
    """Calendar event entity for economic calendar."""
    date: str = ""
    event_name: str = ""
    time: Optional[str] = None
    country: Optional[str] = None
    # Importance: high, medium, low
    importance: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    actual: Optional[str] = None
