"""
Event entities.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .base import Entity


@dataclass
class Event(Entity):
    """Event entity representing extracted news events."""
    title: str = ""
    summary: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    
    # Classification (Layer 1)
    is_market_relevant: bool = True
    category: Optional[str] = None
    region: Optional[str] = None
    linked_indicators: List[str] = field(default_factory=list)
    
    # Scoring (Layer 2)
    base_score: Optional[int] = None
    score_factors: Dict[str, Any] = field(default_factory=dict)
    
    # Ranking (Layer 3)
    current_score: Optional[float] = None
    decay_factor: float = 1.0
    boost_factor: float = 1.0
    display_section: Optional[str] = None
    hot_topic: Optional[str] = None
    
    # Relationships
    is_follow_up: bool = False
    follows_up_on: Optional[str] = None
    
    # Metadata
    published_at: Optional[str] = None
    run_date: Optional[str] = None
    last_ranked_at: Optional[str] = None
    hash: Optional[str] = None


@dataclass
class CausalAnalysis(Entity):
    """Causal analysis entity linking events to causal chains."""
    event_id: str = ""
    template_id: Optional[str] = None
    chain_steps: List[str] = field(default_factory=list)
    confidence: Optional[str] = None
    needs_investigation: List[str] = field(default_factory=list)
    affected_indicators: List[str] = field(default_factory=list)
    impact_on_vn: Optional[str] = None
    reasoning: Optional[str] = None


@dataclass
class TopicFrequency(Entity):
    """Topic frequency entity for hot topic tracking."""
    topic: str = ""
    category: Optional[str] = None
    occurrence_count: int = 1
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    related_event_ids: List[str] = field(default_factory=list)
    is_hot: bool = False
