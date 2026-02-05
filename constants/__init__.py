"""
Constants package for Market Intelligence Dashboard.

Contains shared enums and configuration constants.

Note: Source-specific mappings (indicator IDs, term maps) are now in
      data_transformers/{source}/mappings.py for better modularity.
"""

from .enums import (
    DisplaySection,
    PriorityLevel,
    InvestigationStatus,
    PredictionStatus,
    ConfidenceLevel,
    EvidenceType,
    # Dict versions for backward compatibility
    DISPLAY_SECTIONS,
    PRIORITY_LEVELS,
    INVESTIGATION_STATUSES,
    PREDICTION_STATUSES,
    CONFIDENCE_LEVELS,
    EVIDENCE_TYPES,
)

__all__ = [
    # Enums
    "DisplaySection",
    "PriorityLevel",
    "InvestigationStatus",
    "PredictionStatus",
    "ConfidenceLevel",
    "EvidenceType",
    # Dict versions
    "DISPLAY_SECTIONS",
    "PRIORITY_LEVELS",
    "INVESTIGATION_STATUSES",
    "PREDICTION_STATUSES",
    "CONFIDENCE_LEVELS",
    "EVIDENCE_TYPES",
]
