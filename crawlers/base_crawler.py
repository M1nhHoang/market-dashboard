"""
Base Crawler - Abstract base class for all crawlers
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
import json
import hashlib

from loguru import logger


@dataclass
class CrawlResult:
    """Base result from a crawler."""
    source: str
    crawled_at: datetime
    success: bool
    data: list[dict]
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "crawled_at": self.crawled_at.isoformat(),
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "count": len(self.data)
        }


@dataclass  
class NewsArticle:
    """Standard news article structure."""
    title: str
    content: str
    source: str
    source_url: str
    published_at: datetime
    summary: Optional[str] = None
    raw_html: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "source_url": self.source_url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "summary": self.summary,
        }
    
    def compute_hash(self) -> str:
        """Compute hash for deduplication."""
        content = f"{self.title}|{self.source}|{self.published_at}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class IndicatorData:
    """Standard indicator data structure."""
    id: str
    name: str
    value: float
    unit: str
    category: str
    source: str
    timestamp: datetime
    change: Optional[float] = None
    trend: Optional[str] = None  # 'up', 'down', 'stable'
    
    def to_dict(self) -> dict:
        return asdict(self)


class BaseCrawler(ABC):
    """Abstract base class for all data crawlers."""
    
    def __init__(self, name: str, data_dir: Path):
        self.name = name
        self.data_dir = data_dir
        self.raw_dir = data_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
    @abstractmethod
    async def fetch(self) -> CrawlResult:
        """
        Fetch data from the source.
        Must be implemented by subclasses.
        """
        pass
    
    def save_raw(self, result: CrawlResult, date: Optional[datetime] = None) -> Path:
        """Save raw crawl result to JSON file."""
        if date is None:
            date = datetime.now()
            
        filename = f"{self.name}_{date.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.raw_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            
        logger.info(f"[{self.name}] Saved raw data to {filepath}")
        return filepath
    
    async def run(self) -> CrawlResult:
        """Run the crawler with error handling."""
        logger.info(f"[{self.name}] Starting crawl...")
        
        try:
            result = await self.fetch()
            
            if result.success:
                logger.info(f"[{self.name}] Successfully crawled {len(result.data)} items")
                self.save_raw(result)
            else:
                logger.error(f"[{self.name}] Crawl failed: {result.error}")
                
            return result
            
        except Exception as e:
            logger.exception(f"[{self.name}] Unexpected error during crawl")
            return CrawlResult(
                source=self.name,
                crawled_at=datetime.now(),
                success=False,
                data=[],
                error=str(e)
            )
