"""
Theme Model

Aggregated topic from multiple related events.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Integer, Float, DateTime, Text, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base, TimestampMixin

if TYPE_CHECKING:
    from .signal import Signal


class Theme(Base, TimestampMixin):
    """
    Aggregated topic from multiple related events.
    
    Themes emerge when multiple events share similar topics.
    Strength increases with more evidence and recency.
    Automatically fades when no new events are added.
    
    Statuses:
    - emerging: New theme, strength building (2.0 <= strength < 5.0)
    - active: Strong theme with recent activity (strength >= 5.0)
    - fading: Declining strength, no recent events
    - archived: Strength below threshold, no longer displayed
    """
    __tablename__ = "themes"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Core info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_vi: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Aggregation
    related_event_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    related_signal_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    related_indicators: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, default=1)
    
    # Strength (auto-calculated by background job)
    strength: Mapped[float] = mapped_column(Float, default=1.0, index=True)
    peak_strength: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Timing
    first_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default='emerging', index=True)
    
    # Template link (if derived from causal template)
    template_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships - use string reference to avoid circular import
    signals: Mapped[List["Signal"]] = relationship(
        "Signal",
        backref="theme",
        foreign_keys="Signal.theme_id"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_themes_status_strength', 'status', 'strength'),
    )
