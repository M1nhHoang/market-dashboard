"""
Signal Model

Short-term prediction with auto-verification.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Integer, Float, DateTime, Text, Index, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class Signal(Base, TimestampMixin):
    """
    Short-term prediction with auto-verification.
    
    Created by LLM when analyzing events. Contains specific,
    measurable predictions that can be automatically verified
    against indicator values.
    
    Statuses:
    - active: Prediction pending, not yet expired
    - verified_correct: Prediction verified as correct
    - verified_wrong: Prediction verified as incorrect
    - expired: Deadline passed, no verification possible
    """
    __tablename__ = "signals"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Core prediction
    prediction: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'up', 'down', 'stable'
    target_indicator: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    target_range_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_range_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Confidence & timing
    confidence: Mapped[str] = mapped_column(String(20), default='medium')  # 'high', 'medium', 'low'
    timeframe_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    
    # Source
    source_event_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    source_event_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True
    )
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Verification (auto-populated by background job)
    status: Mapped[str] = mapped_column(String(30), default='active', index=True)
    actual_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    accuracy_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Theme link
    theme_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("themes.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_signals_status_expires', 'status', 'expires_at'),
        Index('idx_signals_confidence', 'confidence'),
    )
