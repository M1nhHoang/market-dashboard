"""
Classifier Module - Layer 1 of the LLM Pipeline

Filters and categorizes news by market relevance.

Components:
- Classifier: Main classification logic using LLM
- ClassificationResult: Data class for classification results
- classify_indicator_data: Rule-based function to separate indicators from news
"""

from .models import ClassificationResult
from .classifier import Classifier, ClassificationError
from .indicator_classifier import classify_indicator_data


__all__ = [
    "Classifier",
    "ClassificationResult",
    "ClassificationError",
    "classify_indicator_data",
]
