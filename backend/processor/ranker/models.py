"""
Data models for the Ranker module.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class RankingResult:
    """Result of ranking an event."""
    event_id: str
    age_days: int
    original_score: float
    decay_factor: float
    boost_factor: float
    final_score: float
    display_section: str
    hot_topic: Optional[str]
    
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "age_days": self.age_days,
            "original_score": self.original_score,
            "decay_factor": self.decay_factor,
            "boost_factor": self.boost_factor,
            "final_score": self.final_score,
            "display_section": self.display_section,
            "hot_topic": self.hot_topic
        }
