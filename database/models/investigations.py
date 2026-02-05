"""
Investigation Models

Models for tracking open questions, evidence, and predictions.
"""
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, Integer, Date, DateTime, Text, Index, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Investigation(Base, TimestampMixin):
    """
    Investigation tracking.
    
    Represents an open question that needs monitoring.
    Created when LLM identifies something that needs verification.
    
    Statuses:
    - open: No new evidence, continue monitoring
    - updated: New evidence found, but not conclusive
    - resolved: Clear answer found
    - stale: No updates for 14+ days
    - escalated: Conflicting evidence, needs human review
    """
    __tablename__ = "investigations"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Core info
    question: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_event_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default='open', index=True)
    priority: Mapped[str] = mapped_column(String(20), default='medium')
    
    # Evidence tracking
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Resolution
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_confidence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    resolved_by_event_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timestamps
    last_evidence_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Related
    related_indicators: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    related_templates: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    evidence: Mapped[List["InvestigationEvidence"]] = relationship(
        "InvestigationEvidence",
        back_populates="investigation",
        cascade="all, delete-orphan",
        order_by="desc(InvestigationEvidence.added_at)"
    )


class InvestigationEvidence(Base):
    """
    Evidence for investigations.
    
    Links events to investigations as supporting, contradicting,
    or neutral evidence.
    """
    __tablename__ = "investigation_evidence"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Foreign keys
    investigation_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Evidence details
    evidence_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'supports', 'contradicts', 'neutral'
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    added_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="evidence")


class Prediction(Base, TimestampMixin):
    """
    Predictions from LLM analysis.
    
    Stores predictions made by the LLM for later verification.
    Helps track prediction accuracy over time.
    Can optionally be linked to an investigation.
    """
    __tablename__ = "predictions"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Prediction content
    prediction: Mapped[str] = mapped_column(Text, nullable=False)
    based_on_events: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    source_event_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Link to investigation (optional)
    investigation_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("investigations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Confidence and timing
    confidence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'high', 'medium', 'low'
    check_by_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    verification_indicator: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Verification
    status: Mapped[str] = mapped_column(String(20), default='pending')  # 'pending', 'verified', 'failed', 'expired'
    actual_outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_predictions_status', 'status'),
        Index('idx_predictions_check_date', 'check_by_date'),
        Index('idx_predictions_investigation', 'investigation_id'),
    )
