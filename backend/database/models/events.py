"""
Event Models

Models for news events, causal analysis, and topic tracking.
"""
from datetime import datetime, date
from typing import Optional, List, Any

from sqlalchemy import String, Float, Integer, Boolean, Date, DateTime, Text, Index, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Event(Base, TimestampMixin):
    """
    Extracted news events.
    
    Represents a news article that has been:
    1. Crawled from a source
    2. Classified by LLM (Layer 1)
    3. Scored by LLM (Layer 2)
    4. Ranked with decay/boost (Layer 3)
    """
    __tablename__ = "events"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Content
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Source
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Classification (Layer 1)
    is_market_relevant: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linked_indicators: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Scoring (Layer 2)
    base_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_factors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Ranking (Layer 3)
    current_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    decay_factor: Mapped[float] = mapped_column(Float, default=1.0)
    boost_factor: Mapped[float] = mapped_column(Float, default=1.0)
    display_section: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hot_topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Relationships (follow-up tracking)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    follows_up_on: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Metadata
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    run_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_ranked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    
    # Relationships
    causal_analysis: Mapped[Optional["CausalAnalysis"]] = relationship(
        "CausalAnalysis",
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan"
    )
    score_history: Mapped[List["ScoreHistory"]] = relationship(
        "ScoreHistory",
        back_populates="event",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_events_display', 'display_section', 'current_score'),
        Index('idx_events_date', 'published_at'),
        Index('idx_events_run_date', 'run_date'),
        Index('idx_events_category', 'category'),
        Index('idx_events_hash', 'hash'),
    )


class CausalAnalysis(Base, TimestampMixin):
    """
    Causal analysis for events.
    
    Links events to causal chain templates and tracks
    the verification status of each step.
    """
    __tablename__ = "causal_analyses"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Foreign key
    event_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Causal chain
    template_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    chain_steps: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'verified', 'likely', 'uncertain'
    
    # Investigation needs
    needs_investigation: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Impact
    affected_indicators: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    impact_on_vn: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="causal_analysis")


class TopicFrequency(Base):
    """
    Topic frequency tracking for hot topics.
    
    Tracks how often topics appear to identify trending themes.
    A topic is "hot" if it appears 3+ times in 7 days.
    """
    __tablename__ = "topic_frequency"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Topic info
    topic: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Tracking
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_seen: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    related_event_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    is_hot: Mapped[bool] = mapped_column(Boolean, default=False)


class ScoreHistory(Base):
    """
    Score history for events.
    
    Tracks how event scores change over time due to decay and boosts.
    Useful for analytics and debugging ranking behavior.
    """
    __tablename__ = "score_history"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Foreign key
    event_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Score data
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    decay_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    boost_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    display_section: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timestamp
    recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="score_history")
