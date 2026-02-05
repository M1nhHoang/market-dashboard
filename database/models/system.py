"""
System Models

Models for system tracking: run history, calendar events, etc.
"""
from datetime import datetime, date, time
from typing import Optional, List

from sqlalchemy import String, Integer, Date, Time, DateTime, Text, Index, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RunHistory(Base):
    """
    Run history for tracking pipeline executions.
    
    Records each pipeline run with statistics and status.
    Useful for monitoring and debugging.
    """
    __tablename__ = "run_history"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Timing
    run_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    run_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Statistics
    news_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    events_extracted: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    events_key: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    events_other: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    investigations_opened: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    investigations_updated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    investigations_resolved: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Raw data tracking (Option A)
    raw_data_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Path to raw JSON file
    sources_crawled: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # ["sbv", "vneconomy"]
    crawl_stats: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"sbv": {"success": 10, "failed": 0}}
    
    # Result
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'success', 'partial', 'failed'


class CalendarEvent(Base):
    """
    Economic calendar events.
    
    Stores upcoming economic events for reference.
    Data from investing.com, forexfactory, etc.
    """
    __tablename__ = "calendar_events"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Event timing
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    
    # Event details
    event_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    importance: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'high', 'medium', 'low'
    
    # Data
    forecast: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    previous: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    actual: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timestamp
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('date', 'event_name', 'country', name='uq_calendar_event'),
        Index('idx_calendar_country', 'country'),
    )
