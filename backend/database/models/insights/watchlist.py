"""
Watchlist Model

User or system-defined alert/trigger.
"""
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, Float, Date, DateTime, Text, Index, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class Watchlist(Base, TimestampMixin):
    """
    User or system-defined alert/trigger.
    
    Monitors for specific conditions and triggers alerts
    when conditions are met.
    
    Trigger types:
    - date: Triggers on a specific date
    - indicator: Triggers when indicator crosses threshold
    - keyword: Triggers when keywords appear in news
    
    Statuses:
    - watching: Actively monitoring
    - triggered: Condition met, alert shown
    - dismissed: User dismissed the alert
    - snoozed: Temporarily hidden
    """
    __tablename__ = "watchlist"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Core info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Trigger conditions
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'date', 'indicator', 'keyword'
    trigger_indicator: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    trigger_condition: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # '> 9.0', '< 25000'
    trigger_keywords: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    trigger_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    
    # Source
    source: Mapped[str] = mapped_column(String(20), default='user')  # 'user', 'system', 'template'
    template_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Related
    related_indicators: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    related_theme_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("themes.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default='watching', index=True)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    triggered_by_event_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True
    )
    trigger_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Actual value when triggered
    
    # Snooze
    snoozed_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Created by
    created_by: Mapped[str] = mapped_column(String(50), default='system')  # 'system' or user_id
    
    # Indexes
    __table_args__ = (
        Index('idx_watchlist_status_type', 'status', 'trigger_type'),
        Index('idx_watchlist_trigger_date', 'trigger_date'),
    )
