"""
Insight Models - Signals, Themes, and Watchlist

Replaces the Investigation system with measurable, auto-verifiable insights:
- Signals: Short-term predictions with auto-verification
- Themes: Aggregated topics from multiple events
- Watchlist: User/system-defined alerts and triggers
"""

from .signal import Signal
from .theme import Theme
from .watchlist import Watchlist
from .signal_accuracy_stats import SignalAccuracyStats

__all__ = [
    "Signal",
    "Theme",
    "Watchlist",
    "SignalAccuracyStats",
]
