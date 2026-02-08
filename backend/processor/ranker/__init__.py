"""
Ranker Module - Layer 3 of the LLM Pipeline

Applies time decay and boost factors, assigns display sections.

Components:
- Ranker: Main ranking logic
- RankingResult: Data class for ranking results
- Decay/boost configuration and utilities
"""

from .models import RankingResult
from .config import (
    DECAY_SCHEDULE,
    BOOST_FOLLOW_UP,
    BOOST_HOT_TOPIC,
    BOOST_MULTI_INDICATOR,
    THRESHOLD_KEY_EVENTS,
    THRESHOLD_OTHER_NEWS,
    MAX_KEY_EVENTS,
    get_decay_factor,
    calculate_boost_factor,
    determine_display_section,
)
from .ranker import Ranker


__all__ = [
    # Main classes
    "Ranker",
    # Models
    "RankingResult",
    # Config
    "DECAY_SCHEDULE",
    "BOOST_FOLLOW_UP",
    "BOOST_HOT_TOPIC",
    "BOOST_MULTI_INDICATOR",
    "THRESHOLD_KEY_EVENTS",
    "THRESHOLD_OTHER_NEWS",
    "MAX_KEY_EVENTS",
    # Utilities
    "get_decay_factor",
    "calculate_boost_factor",
    "determine_display_section",
]
