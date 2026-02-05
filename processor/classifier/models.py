"""
Data models for the Classifier module.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    """Result of classifying a single news item."""
    is_market_relevant: bool
    category: Optional[str]
    linked_indicators: list[str]
    reasoning: str
    raw_output: str
    
    def to_dict(self) -> dict:
        return {
            "is_market_relevant": self.is_market_relevant,
            "category": self.category,
            "linked_indicators": self.linked_indicators,
            "reasoning": self.reasoning
        }
