"""
Indicator Models

Models for market indicators and their historical values.
"""
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, Float, Date, DateTime, Text, Index, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Indicator(Base, TimestampMixin):
    """
    Current indicator values.
    
    Stores the latest value for each indicator.
    Historical values are stored in IndicatorHistory.
    
    Examples:
        - interbank_on: Interbank overnight rate
        - usd_vnd_central: Central exchange rate
        - gold_sjc: SJC gold price
        - cpi_mom: CPI month-over-month
    """
    __tablename__ = "indicators"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Basic info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_vi: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Categorization
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Current value
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Change tracking
    change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trend: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'up', 'down', 'stable'
    
    # Source
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Extra metadata (JSON string)
    attributes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    history: Mapped[List["IndicatorHistory"]] = relationship(
        "IndicatorHistory",
        back_populates="indicator",
        cascade="all, delete-orphan",
        order_by="desc(IndicatorHistory.date)"
    )


class IndicatorHistory(Base):
    """
    Indicator history for trend analysis.
    
    Stores historical values with timestamps for charting and analysis.
    Unique constraint on (indicator_id, date, value) prevents duplicates.
    """
    __tablename__ = "indicator_history"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Foreign key
    indicator_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("indicators.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Value data
    value: Mapped[float] = mapped_column(Float, nullable=False)
    previous_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # For interbank rates
    
    # Timestamps
    date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Source
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Relationships
    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="history")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('indicator_id', 'date', 'value', name='uq_indicator_date_value'),
        Index('idx_indicator_history_lookup', 'indicator_id', 'date'),
    )
