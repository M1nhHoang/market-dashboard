"""
News Crawler - RSS feeds and news APIs

⚠️ PLACEHOLDER - Needs actual RSS feeds/APIs from user

Expected sources:
- VnEconomy
- CafeF
- VnExpress Economy
- Other financial news sources
"""
from datetime import datetime
from typing import Optional
from pathlib import Path

import httpx
import feedparser
from bs4 import BeautifulSoup
from loguru import logger

from .base_crawler import BaseCrawler, CrawlResult, NewsArticle


class NewsCrawler(BaseCrawler):
    """
    Crawler for financial news from RSS feeds and APIs.
    
    TODO: User needs to provide:
    - List of RSS feed URLs
    - Any API endpoints for news
    - Content extraction rules (if needed)
    """
    
    def __init__(self, data_dir: Path):
        super().__init__("news", data_dir)
        
        # TODO: Replace with actual feeds from user
        self.rss_feeds = {
            # "vneconomy": "https://vneconomy.vn/rss/...",
            # "cafef": "https://cafef.vn/rss/...",
            # "vnexpress": "https://vnexpress.net/rss/kinh-doanh.rss",
        }
        
        self.headers = {
            "User-Agent": "MarketIntelligence/1.0"
        }
        
    async def fetch(self) -> CrawlResult:
        """
        Fetch news from all configured sources.
        
        ⚠️ PLACEHOLDER IMPLEMENTATION
        """
        logger.warning("[News] Using placeholder - need actual RSS feeds/APIs")
        
        if not self.rss_feeds:
            return CrawlResult(
                source="news",
                crawled_at=datetime.now(),
                success=False,
                data=[],
                error="Placeholder: No RSS feeds configured. User needs to provide feed URLs."
            )
        
        all_articles = []
        errors = []
        
        for source_name, feed_url in self.rss_feeds.items():
            try:
                articles = await self._fetch_rss(source_name, feed_url)
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"[News] Failed to fetch {source_name}: {e}")
                errors.append(f"{source_name}: {str(e)}")
        
        return CrawlResult(
            source="news",
            crawled_at=datetime.now(),
            success=len(all_articles) > 0,
            data=[a.to_dict() for a in all_articles],
            error="; ".join(errors) if errors else None
        )
    
    async def _fetch_rss(self, source_name: str, feed_url: str) -> list[NewsArticle]:
        """Fetch and parse a single RSS feed."""
        async with httpx.AsyncClient() as client:
            response = await client.get(feed_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
        feed = feedparser.parse(response.text)
        articles = []
        
        for entry in feed.entries:
            try:
                article = NewsArticle(
                    title=entry.get("title", ""),
                    content=self._extract_content(entry),
                    source=source_name,
                    source_url=entry.get("link", ""),
                    published_at=self._parse_date(entry.get("published")),
                    summary=entry.get("summary", "")
                )
                articles.append(article)
            except Exception as e:
                logger.warning(f"[News] Failed to parse entry from {source_name}: {e}")
                
        return articles
    
    def _extract_content(self, entry) -> str:
        """Extract content from RSS entry."""
        # Try different content fields
        content = ""
        
        if hasattr(entry, "content"):
            content = entry.content[0].value if entry.content else ""
        elif hasattr(entry, "summary"):
            content = entry.summary
        elif hasattr(entry, "description"):
            content = entry.description
            
        # Strip HTML tags
        if content:
            soup = BeautifulSoup(content, "html.parser")
            content = soup.get_text(strip=True)
            
        return content
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string from RSS feed."""
        if not date_str:
            return None
            
        try:
            from dateutil import parser
            return parser.parse(date_str)
        except Exception:
            return None


# ============================================================
# INSTRUCTIONS FOR USER
# ============================================================
"""
To complete this crawler, please provide:

1. RSS Feed URLs:
   - VnEconomy RSS feed URL
   - CafeF RSS feed URL
   - VnExpress Economy RSS feed URL
   - Any other financial news RSS feeds

2. For each feed, please test and confirm:
   - The feed is accessible
   - Sample of what entries look like
   
Example format to provide:
```
VnEconomy: https://vneconomy.vn/rss/kinh-te.rss
CafeF: https://cafef.vn/rss/thi-truong.rss

Sample entry:
{
  "title": "NHNN bơm ròng 25.000 tỷ đồng...",
  "link": "https://...",
  "published": "Mon, 03 Feb 2026 08:00:00 +0700",
  "summary": "..."
}
```

3. If any source requires API instead of RSS:
   - Provide cURL command
   - Sample response
"""
