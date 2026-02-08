"""
Data models for the Scorer module.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SignalOutput:
    """Signal output from scoring."""
    create_signal: bool = False
    prediction: Optional[str] = None
    target_indicator: Optional[str] = None
    direction: Optional[str] = None  # 'up', 'down', 'stable'
    target_range_low: Optional[float] = None
    target_range_high: Optional[float] = None
    confidence: str = "medium"
    timeframe_days: Optional[int] = None
    reasoning: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "create_signal": self.create_signal,
            "prediction": self.prediction,
            "target_indicator": self.target_indicator,
            "direction": self.direction,
            "target_range_low": self.target_range_low,
            "target_range_high": self.target_range_high,
            "confidence": self.confidence,
            "timeframe_days": self.timeframe_days,
            "reasoning": self.reasoning,
        }


@dataclass
class ThemeLink:
    """Theme link output from scoring."""
    existing_theme_id: Optional[str] = None
    create_new_theme: bool = False
    new_theme: Optional[dict] = None  # {name, name_vi, description}
    
    def to_dict(self) -> dict:
        return {
            "existing_theme_id": self.existing_theme_id,
            "create_new_theme": self.create_new_theme,
            "new_theme": self.new_theme,
        }


@dataclass
class ScoringResult:
    """Result of scoring a single news item."""
    base_score: int
    score_factors: dict
    causal_analysis: dict
    signal_output: Optional[SignalOutput] = None
    theme_link: Optional[ThemeLink] = None
    raw_output: str = ""
    parse_error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "base_score": self.base_score,
            "score_factors": self.score_factors,
            "causal_analysis": self.causal_analysis,
            "signal_output": self.signal_output.to_dict() if self.signal_output else None,
            "theme_link": self.theme_link.to_dict() if self.theme_link else None,
        }
