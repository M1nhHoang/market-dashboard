"""
Configuration and utilities for event ranking.

Contains:
- Decay schedule and factor calculation
- Boost factors
- Display section thresholds
- Utility functions for ranking calculations
"""
import json


# ============================================
# DECAY CONFIGURATION
# ============================================

DECAY_SCHEDULE = {
    # age_days: decay_factor
    0: 1.0,      # Today: 100%
    1: 0.95,     # 1 day: 95%
    2: 0.90,     # 2 days: 90%
    3: 0.85,     # 3 days: 85%
    4: 0.75,     # 4-5 days: 75%
    5: 0.75,
    6: 0.70,     # 6-7 days: 70%
    7: 0.70,
    8: 0.55,     # 8-14 days: 55%
    14: 0.55,
    15: 0.35,    # 15-30 days: 35%
    30: 0.35,
    31: 0.0      # 30+ days: Archive
}


# ============================================
# BOOST FACTORS
# ============================================

BOOST_FOLLOW_UP = 1.20      # +20% for theme-related events
BOOST_HOT_TOPIC = 1.15      # +15% for hot topic
BOOST_MULTI_INDICATOR = 1.10  # +10% for connecting 2+ indicators


# ============================================
# DISPLAY THRESHOLDS
# ============================================

THRESHOLD_KEY_EVENTS = 50    # final_score >= 50 AND has linked_indicators
THRESHOLD_OTHER_NEWS = 20    # final_score >= 20
MAX_KEY_EVENTS = 15          # Maximum in key_events section


# ============================================
# UTILITY FUNCTIONS
# ============================================

def get_decay_factor(age_days: int) -> float:
    """
    Get decay factor for given age in days.
    
    Args:
        age_days: Number of days since event was published
        
    Returns:
        Decay factor between 0.0 and 1.0
    """
    if age_days >= 31:
        return 0.0  # Archive
    
    # Find the closest age bracket
    for day in sorted(DECAY_SCHEDULE.keys(), reverse=True):
        if age_days >= day:
            return DECAY_SCHEDULE[day]
    
    return 1.0


def calculate_boost_factor(
    event: dict,
    active_themes: list[str] = None,
    hot_topics: list[str] = None
) -> float:
    """
    Calculate boost factor for an event.
    
    Boosts are applied for:
    - Part of active theme (+20%)
    - Part of hot topic (+15%)
    - Connects 2+ indicators (+10%)
    
    Args:
        event: Event dict with metadata
        active_themes: List of active theme names
        hot_topics: List of hot topic names
        
    Returns:
        Combined boost factor (multiplicative)
    """
    boost = 1.0
    active_themes = active_themes or []
    hot_topics = hot_topics or []
    
    # Theme boost - if event is part of an active theme
    event_category = event.get('category') or ''
    event_title = event.get('title') or ''
    event_title = event_title.lower()
    for theme_name in active_themes:
        if theme_name.lower() in event_title or theme_name.lower() in event_category.lower():
            boost *= BOOST_FOLLOW_UP  # Reuse the 20% boost
            break
    
    # Hot topic boost
    if event.get('hot_topic') and event.get('hot_topic') in hot_topics:
        boost *= BOOST_HOT_TOPIC
    
    # Multi-indicator boost
    linked = event.get('linked_indicators', [])
    if isinstance(linked, str):
        linked = json.loads(linked) if linked else []
    if len(linked) >= 2:
        boost *= BOOST_MULTI_INDICATOR
    
    return boost


def determine_display_section(
    final_score: float,
    linked_indicators: list,
    age_days: int,
    is_market_relevant: bool = True
) -> str:
    """
    Determine which display section an event belongs to.
    
    Sections:
    - key_events: High score with linked indicators
    - other_news: Market relevant with moderate score
    - archive: Old, low score, or not relevant
    
    Args:
        final_score: Calculated final score after decay/boost
        linked_indicators: List of linked indicator IDs
        age_days: Days since publication
        is_market_relevant: Whether event is market relevant
        
    Returns:
        Section name: 'key_events', 'other_news', or 'archive'
    """
    if age_days >= 31:
        return 'archive'
    
    if not is_market_relevant:
        return 'archive'
    
    if final_score < THRESHOLD_OTHER_NEWS:
        return 'archive'
    
    has_indicators = bool(linked_indicators)
    if final_score >= THRESHOLD_KEY_EVENTS and has_indicators:
        return 'key_events'
    
    return 'other_news'
