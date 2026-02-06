"""
Shared Enums

Application-wide enums used across multiple modules.
These are not source-specific and apply to the entire system.
"""
from enum import Enum


class DisplaySection(str, Enum):
    """Event display sections in UI."""
    KEY_EVENTS = "key_events"
    OTHER_NEWS = "other_news"
    ARCHIVE = "archive"


class PriorityLevel(str, Enum):
    """Priority levels for investigations."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InvestigationStatus(str, Enum):
    """Investigation status states."""
    OPEN = "open"
    UPDATED = "updated"
    RESOLVED = "resolved"
    STALE = "stale"
    ESCALATED = "escalated"


class PredictionStatus(str, Enum):
    """Prediction verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class ConfidenceLevel(str, Enum):
    """Confidence levels for analyses."""
    VERIFIED = "verified"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"


class EvidenceType(str, Enum):
    """Types of evidence for investigations."""
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


# Dict versions for backward compatibility
DISPLAY_SECTIONS = {s.value: s.value for s in DisplaySection}
PRIORITY_LEVELS = {p.value: p.value for p in PriorityLevel}
INVESTIGATION_STATUSES = {s.value: s.value for s in InvestigationStatus}
PREDICTION_STATUSES = {s.value: s.value for s in PredictionStatus}
CONFIDENCE_LEVELS = {c.value: c.value for c in ConfidenceLevel}
EVIDENCE_TYPES = {e.value: e.value for e in EvidenceType}
