"""
Processor package for Market Intelligence Dashboard.

3-Layer LLM Pipeline:
- Layer 1: Classifier - Filter and categorize news
- Layer 2: Scorer - Score and analyze relevant news
- Layer 3: Ranker - Rank and decay all active events

Main entry point: Pipeline class
"""

from .classifier import Classifier, ClassificationResult, classify_indicator_data
from .scorer import Scorer, ScoringResult, generate_context_summary
from .ranker import (
    Ranker,
    InvestigationReviewer,
    RankingResult,
    get_decay_factor,
    calculate_boost_factor,
    determine_display_section,
)
from .context_builder import ContextBuilder
from .output_parser import OutputParser, ParsedAnalysis
from .pipeline import Pipeline

__all__ = [
    # Pipeline
    "Pipeline",
    # Layer 1: Classifier
    "Classifier",
    "ClassificationResult",
    "classify_indicator_data",
    # Layer 2: Scorer
    "Scorer",
    "ScoringResult",
    "generate_context_summary",
    # Layer 3: Ranker
    "Ranker",
    "InvestigationReviewer",
    "RankingResult",
    "get_decay_factor",
    "calculate_boost_factor",
    "determine_display_section",
    # Utilities
    "ContextBuilder",
    "OutputParser",
    "ParsedAnalysis",
]
