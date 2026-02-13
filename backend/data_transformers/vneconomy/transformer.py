"""
VnEconomy Transformer - Transform VnEconomy crawler output to CrawlerOutput.

Converts VnEconomyCrawler output to EventRecord format for LLM pipeline.
"""
from datetime import datetime
from typing import Dict, Any, Optional

from loguru import logger

from data_transformers.base import BaseTransformer
from data_transformers.models import (
    CrawlerOutput,
    EventRecord,
    EventType,
)


class VnEconomyTransformer(BaseTransformer):
    """
    Transform VnEconomy crawler output to CrawlerOutput format.
    
    News articles → EventRecords (news type) → LLM pipeline analysis
    """
    
    @property
    def source_name(self) -> str:
        return "vneconomy"
    
    def transform(self, raw_data: Dict[str, Any]) -> CrawlerOutput:
        """
        Transform raw crawler data to CrawlerOutput.
        
        Args:
            raw_data: Raw output from VnEconomyCrawler.run().to_dict()
            
        Returns:
            CrawlerOutput with events list (no metrics or calendar for news)
        """
        # Parse crawled_at
        crawled_at = self._parse_datetime(raw_data.get("crawled_at"))
        
        # Check success
        if not raw_data.get("success", False):
            logger.warning(f"[VnEconomyTransformer] Crawl failed, returning empty output")
            return CrawlerOutput(
                source=self.source_name,
                crawled_at=crawled_at,
                success=False,
                error=raw_data.get("error"),
                metrics=[],
                events=[],
                calendar=[],
            )
        
        # Get data array
        data_items = raw_data.get("data", [])
        events = []
        
        for item in data_items:
            # Skip metadata items
            if item.get("type") == "metadata":
                continue
            
            event = self._transform_news_item(item)
            if event:
                events.append(event)
        
        logger.info(f"[VnEconomyTransformer] Transformed {len(events)} news items to events")
        
        return CrawlerOutput(
            source=self.source_name,
            crawled_at=crawled_at,
            success=True,
            metrics=[],  # News doesn't produce metrics
            events=events,
            calendar=[],  # News doesn't produce calendar events
        )
    
    def _transform_news_item(self, item: dict) -> Optional[EventRecord]:
        """Transform a single news item to EventRecord."""
        try:
            title = item.get("title", "").strip()
            if not title:
                return None
            
            # Source URL is required
            source_url = item.get("source_url", "")
            if not source_url:
                return None
            
            # Content could be empty if fetch failed
            content = item.get("content", "") or ""
            summary = item.get("summary", "") or ""
            
            # Parse publish date
            published_at = self._parse_datetime(item.get("published_at"))
            
            # Determine if we have full content
            has_full_content = bool(content) and item.get("fetch_success", True)
            
            # Build categories list from category field
            category = item.get("category")
            categories = [category] if category else []
            
            return EventRecord(
                event_type=EventType.NEWS,
                title=title,
                summary=summary,
                content=content,
                published_at=published_at,
                source=self.source_name,
                source_url=source_url,
                language="vi",
                categories=categories,
                has_full_content=has_full_content,
                attachments=[],
            )
            
        except Exception as e:
            logger.error(f"[VnEconomyTransformer] Error transforming item: {e}")
            return None
    
    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if value is None:
            return datetime.now()
            
        if isinstance(value, datetime):
            return value
            
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
            
            try:
                from dateutil import parser
                return parser.parse(value)
            except Exception:
                pass
        
        return datetime.now()
