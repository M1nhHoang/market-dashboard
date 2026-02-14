"""
Scorer Module - Layer 2 of the LLM Pipeline

Scores and analyzes market-relevant news.

Components:
- Scorer: Main scoring logic with causal analysis
- ScoringResult: Data class for scoring results
- generate_context_summary: Utility to summarize previous context
"""

from .models import ScoringResult
from .scorer import Scorer, ScoringError
from .context_summary import generate_context_summary


__all__ = [
    "Scorer",
    "ScoringResult",
    "ScoringError",
    "generate_context_summary",
]
