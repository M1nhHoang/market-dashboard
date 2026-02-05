"""
Investigation entities.
"""
from dataclasses import dataclass, field
from typing import Optional, List

from .base import Entity


@dataclass
class Investigation(Entity):
    """Investigation entity for tracking open questions."""
    question: str = ""
    context: Optional[str] = None
    source_event_id: Optional[str] = None
    
    # Status: open, updated, resolved, stale, escalated
    status: str = "open"
    # Priority: high, medium, low
    priority: str = "medium"
    
    # Evidence tracking
    evidence_count: int = 0
    evidence_summary: Optional[str] = None
    
    # Resolution
    resolution: Optional[str] = None
    resolution_confidence: Optional[str] = None
    resolved_by_event_id: Optional[str] = None
    
    # Timestamps
    last_evidence_at: Optional[str] = None
    resolved_at: Optional[str] = None
    
    # Related items
    related_indicators: List[str] = field(default_factory=list)
    related_templates: List[str] = field(default_factory=list)
    
    # Joined field (from source event)
    source_event_title: Optional[str] = None


@dataclass
class InvestigationEvidence(Entity):
    """Evidence linked to an investigation."""
    investigation_id: str = ""
    event_id: str = ""
    # Evidence type: supports, contradicts, neutral
    evidence_type: str = "neutral"
    summary: Optional[str] = None
    added_at: Optional[str] = None


@dataclass
class Prediction(Entity):
    """Prediction entity for tracking forecasts."""
    prediction: str = ""
    based_on_events: List[str] = field(default_factory=list)
    source_event_id: Optional[str] = None
    confidence: Optional[str] = None
    check_by_date: Optional[str] = None
    verification_indicator: Optional[str] = None
    # Status: pending, verified, failed, expired
    status: str = "pending"
    actual_outcome: Optional[str] = None
    verified_at: Optional[str] = None
