"""
Base Transformer Interface

All source-specific transformers must inherit from BaseTransformer
and implement the transform() method.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from data_transformers.models import CrawlerOutput


class BaseTransformer(ABC):
    """
    Abstract base class for all data transformers.
    
    Each data source (SBV, Yahoo, Investing, etc.) should have
    its own transformer class that converts the raw crawler output
    to the unified CrawlerOutput structure.
    
    Usage:
        transformer = SBVTransformer()
        output = transformer.transform(raw_data)
    """
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source name (e.g., 'sbv', 'yahoo', 'investing')."""
        pass
    
    @abstractmethod
    def transform(self, raw_data: List[Dict[str, Any]]) -> CrawlerOutput:
        """
        Transform raw crawler data to unified CrawlerOutput.
        
        Args:
            raw_data: Raw data from crawler.fetch()
                     (format varies by source)
        
        Returns:
            CrawlerOutput with metrics, events, calendar populated
        """
        pass
    
    def validate_raw_data(self, raw_data: Any) -> bool:
        """
        Validate raw data before transformation.
        
        Override in subclass for source-specific validation.
        
        Returns:
            True if data is valid, False otherwise
        """
        if raw_data is None:
            return False
        if isinstance(raw_data, list):
            return len(raw_data) > 0
        if isinstance(raw_data, dict):
            return len(raw_data) > 0
        return False
