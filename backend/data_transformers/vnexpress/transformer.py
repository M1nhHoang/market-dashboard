"""
VnExpress Transformer - Transform VnExpress crawler output to CrawlerOutput.

Converts VnExpressCrawler output to EventRecord format for LLM pipeline.
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


class VnExpressTransformer(BaseTransformer):
    """
    Transform VnExpress crawler output to CrawlerOutput format.
    
    News articles → EventRecords (news type) → LLM pipeline analysis
    """
    
    @property
    def source_name(self) -> str:
        return "vnexpress"
    
    def transform(self, raw_data: Dict[str, Any]) -> CrawlerOutput:
        """
        Transform raw crawler data to CrawlerOutput.
        
        Args:
            raw_data: Raw output from VnExpressCrawler.run().to_dict()
            
        Returns:
            CrawlerOutput with events list
        """
        # Parse crawled_at
        crawled_at = self._parse_datetime(raw_data.get("crawled_at"))
        
        # Check success
        if not raw_data.get("success", False):
            logger.warning(f"[VnExpressTransformer] Crawl failed, returning empty output")
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
            if item.get("type") == "metadata":
                continue
            event = self._transform_item(item)
            if event:
                events.append(event)
        
        logger.info(f"[VnExpressTransformer] Transformed {len(events)} items to events")
        
        return CrawlerOutput(
            source=self.source_name,
            crawled_at=crawled_at,
            success=True,
            metrics=[],
            events=events,
            calendar=[],
        )
    
    def _transform_item(self, item: dict) -> Optional[EventRecord]:
        """Transform a single item to EventRecord."""
        try:
            title = item.get("title", "").strip()
            if not title:
                return None
            
            source_url = item.get("source_url", "")
            if not source_url:
                return None
            
            content = item.get("content", "") or ""
            summary = item.get("summary", "") or ""
            published_at = self._parse_datetime(item.get("published_at"))
            has_full_content = bool(content)
            
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
            logger.error(f"[VnExpressTransformer] Error transforming item: {e}")
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
        return datetime.now()
