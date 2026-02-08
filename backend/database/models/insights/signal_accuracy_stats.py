"""
Signal Accuracy Stats Model

Aggregated accuracy statistics for signals.
"""
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Float, Date, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class SignalAccuracyStats(Base):
    """
    Aggregated accuracy statistics for signals.
    
    Updated daily by background job.
    Tracks accuracy by confidence level, indicator, and time period.
    """
    __tablename__ = "signal_accuracy_stats"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Grouping
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly', 'all_time'
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Filter (optional - for breakdown)
    confidence_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'high', 'medium', 'low', or NULL for all
    indicator_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # or NULL for all
    
    # Stats
    total_signals: Mapped[int] = mapped_column(Integer, default=0)
    verified_correct: Mapped[int] = mapped_column(Integer, default=0)
    verified_wrong: Mapped[int] = mapped_column(Integer, default=0)
    expired: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # verified_correct / (verified_correct + verified_wrong)
    
    # Timestamp
    calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_accuracy_period', 'period', 'period_start'),
    )
