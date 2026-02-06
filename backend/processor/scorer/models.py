"""
Data models for the Scorer module.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScoringResult:
    """Result of scoring a single news item."""
    base_score: int
    score_factors: dict
    causal_analysis: dict
    is_follow_up: bool
    follows_up_on: Optional[str]
    investigation_action: dict
    predictions: list[dict]
    raw_output: str
    parse_error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "base_score": self.base_score,
            "score_factors": self.score_factors,
            "causal_analysis": self.causal_analysis,
            "is_follow_up": self.is_follow_up,
            "follows_up_on": self.follows_up_on,
            "investigation_action": self.investigation_action,
            "predictions": self.predictions
        }
