"""
VnExpress Crawler - Vietnamese Financial News

Extract news from VnExpress Economy section (https://vnexpress.net/kinh-doanh)

Categories to crawl:
- /kinh-doanh - Kinh doanh (Business - main)
- /kinh-doanh/chung-khoan - Chứng khoán (Stock market)
- /kinh-doanh/tai-chinh - Tài chính (Finance)
- /kinh-doanh/vi-mo - Vĩ mô (Macro)

Architecture:
- Crawl category pages to get article list
- Fetch each article for full content + publish date
- Transform to EventRecord for LLM pipeline
"""
import re
import json
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from .base_crawler import BaseCrawler, CrawlResult
from data_transformers.vnexpress import VnExpressTransformer


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class VnExpressNewsItem:
    """News item extracted from VnExpress category page."""
    title: str
    url: str
    category: Optional[str] = None
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    source: str = "vnexpress"


@dataclass 
class VnExpressArticleContent:
    """Full article content from VnExpress."""
    title: str
    url: str
    content: str
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    source: str = "vnexpress"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "news",
            "title": self.title,
            "source_url": self.url,
            "content": self.content,
            "summary": self.summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "source": self.source,
        }


# ============================================================
# VNEXPRESS CRAWLER
# ============================================================

class VnExpressCrawler(BaseCrawler):
    """
    Crawler for VnExpress Economy (https://vnexpress.net/kinh-doanh)
    
    Crawls category pages to extract news articles.
    
    Categories:
    - kinh-doanh: Kinh doanh (Business - main)
    - kinh-doanh/chung-khoan: Chứng khoán (Stock market)
    - kinh-doanh/tai-chinh: Tài chính (Finance)
    - kinh-doanh/vi-mo: Vĩ mô (Macro)
    
    Flow:
    1. fetch() - Get article list from category pages
    2. fetch_article_content() - Get full content per article
    3. run() - Full crawl with content extraction
    """
    
    BASE_URL = "https://vnexpress.net"
    
    # Category URLs to crawl with their display names
    CATEGORIES = {
        "kinh-doanh": "Kinh doanh",
        "kinh-doanh/chung-khoan": "Chứng khoán",
        "kinh-doanh/tai-chinh": "Tài chính",
        "kinh-doanh/vi-mo": "Vĩ mô",
    }
    
    # Headers to mimic browser
    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    }
    
    def __init__(self, data_dir: Path):
        super().__init__(name="vnexpress", data_dir=data_dir)
        self.source = "vnexpress"
        self._transformer = VnExpressTransformer()
    
    @property
    def transformer(self):
        """Return the transformer for this crawler."""
        return self._transformer
    
    def _make_absolute_url(self, href: str) -> str:
        """Convert relative URL to absolute."""
        if not href:
            return ""
        if href.startswith("http"):
            return href
        if href.startswith("//"):
            return f"https:{href}"
        if href.startswith("/"):
            return f"{self.BASE_URL}{href}"
        return f"{self.BASE_URL}/{href}"
    
    def _clean_text(self, text: Optional[str]) -> str:
        """Clean text content."""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _parse_vnexpress_datetime(self, time_str: str) -> Optional[datetime]:
        """
        Parse VnExpress datetime formats.
        
        Formats:
        - Timestamp: "1707714000" (Unix timestamp)
        - Display: "Thứ hai, 12/2/2026, 10:00 (GMT+7)"
        - ISO: "2026-02-12T10:00:00+07:00"
        """
        if not time_str:
            return None
        
        time_str = time_str.strip()
        
        # Try Unix timestamp
        if time_str.isdigit():
            try:
                return datetime.fromtimestamp(int(time_str))
            except (ValueError, OSError):
                pass
        
        # Try ISO format
        try:
            return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except ValueError:
            pass
        
        # Try display format: "Thứ hai, 12/2/2026, 10:00 (GMT+7)"
        try:
            # Extract date part
            match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4}),?\s*(\d{1,2}):(\d{2})', time_str)
            if match:
                day, month, year, hour, minute = match.groups()
                return datetime(int(year), int(month), int(day), int(hour), int(minute))
        except ValueError:
            pass
        
        return None
    
    async def fetch(self, categories: Optional[List[str]] = None) -> CrawlResult:
        """
        Fetch article list from VnExpress category pages.
        
        Args:
            categories: List of category slugs to crawl. 
                        Default: all defined categories.
        
        Returns:
            CrawlResult with list of news items (no full content yet)
        """
        if categories is None:
            categories = list(self.CATEGORIES.keys())
        
        all_items: List[VnExpressNewsItem] = []
        
        async with httpx.AsyncClient(
            timeout=30.0, 
            headers=self.HEADERS,
            verify=False,
            follow_redirects=True,
        ) as client:
            for cat_slug in categories:
                cat_name = self.CATEGORIES.get(cat_slug, cat_slug)
                url = f"{self.BASE_URL}/{cat_slug}"
                
                logger.info(f"[vnexpress] Fetching {cat_name}: {url}")
                
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    items = self._parse_category_page(
                        response.text, 
                        category=cat_name
                    )
                    all_items.extend(items)
                    logger.info(f"[vnexpress] Found {len(items)} articles in {cat_name}")
                    
                except Exception as e:
                    logger.error(f"[vnexpress] Error fetching {cat_name}: {e}")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_items = []
        for item in all_items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)
        
        logger.info(f"[vnexpress] Found {len(unique_items)} unique articles")
        
        return CrawlResult(
            source=self.source,
            crawled_at=datetime.now(),
            success=True,
            data=[self._item_to_dict(item) for item in unique_items],
            error=None,
        )
    
    def _item_to_dict(self, item: VnExpressNewsItem) -> Dict[str, Any]:
        """Convert NewsItem to dict for CrawlResult."""
        return {
            "type": "news",
            "title": item.title,
            "source_url": item.url,
            "category": item.category,
            "summary": item.summary,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "source": item.source,
        }
    
    def _parse_category_page(self, html: str, category: str) -> List[VnExpressNewsItem]:
        """
        Parse VnExpress category page HTML.
        
        VnExpress structure:
        - Featured: .item-news.item-news-common.full-thumb
        - List items: .item-news.item-news-common
        - Title in: .title-news a
        - Summary in: .description a
        - Time in: .time-count (data-timestamp attribute) or span.time
        """
        soup = BeautifulSoup(html, "html.parser")
        items: List[VnExpressNewsItem] = []
        
        # Find all article items
        for article in soup.find_all("article", class_="item-news"):
            item = self._parse_article_item(article, category)
            if item:
                items.append(item)
        
        # Also check for .item-news-common divs (alternative structure)
        for div in soup.find_all("div", class_="item-news-common"):
            if div.find_parent("article", class_="item-news"):
                continue  # Already processed
            item = self._parse_article_item(div, category)
            if item:
                items.append(item)
        
        return items
    
    def _parse_article_item(self, elem, category: str) -> Optional[VnExpressNewsItem]:
        """Parse a single article item from category page."""
        try:
            # Title and URL from .title-news a
            title_elem = elem.find("h3", class_="title-news") or elem.find("h2", class_="title-news")
            if not title_elem:
                title_elem = elem.find(class_="title-news")
            
            if not title_elem:
                return None
            
            link = title_elem.find("a")
            if not link:
                return None
            
            title = link.get("title", "") or link.get_text(strip=True)
            href = link.get("href", "")
            
            if not title or not href:
                return None
            
            # Skip video/photo/infographic content
            if any(x in href for x in ["/video/", "/photo/", "/infographics/"]):
                return None
            
            # Summary from .description a
            summary = None
            desc_elem = elem.find("p", class_="description")
            if desc_elem:
                desc_link = desc_elem.find("a")
                if desc_link:
                    summary = desc_link.get_text(strip=True)
                else:
                    summary = desc_elem.get_text(strip=True)
            
            # Time from data-timestamp or .time-count
            published_at = None
            time_elem = elem.find(class_="time-count")
            if time_elem:
                timestamp = time_elem.get("data-timestamp")
                if timestamp:
                    published_at = self._parse_vnexpress_datetime(timestamp)
            
            if not published_at:
                # Try span.time
                time_span = elem.find("span", class_="time")
                if time_span:
                    time_str = time_span.get_text(strip=True)
                    published_at = self._parse_vnexpress_datetime(time_str)
            
            return VnExpressNewsItem(
                title=self._clean_text(title),
                url=self._make_absolute_url(href),
                category=category,
                summary=self._clean_text(summary) if summary else None,
                published_at=published_at,
            )
        except Exception as e:
            logger.debug(f"[vnexpress] Error parsing article item: {e}")
            return None
    
    async def fetch_article_content(self, url: str) -> Optional[VnExpressArticleContent]:
        """
        Fetch full content from a VnExpress article URL.
        
        Args:
            url: Full URL to the article
            
        Returns:
            VnExpressArticleContent or None if failed
        """
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                headers=self.HEADERS,
                verify=False,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                return self._parse_article_page(response.text, url)
                
        except Exception as e:
            logger.error(f"[vnexpress] Error fetching article {url}: {e}")
            return None
    
    def _parse_article_page(self, html: str, url: str) -> Optional[VnExpressArticleContent]:
        """
        Parse VnExpress article page.
        
        Article structure:
        - Title: h1.title-detail
        - Summary: p.description
        - Content: article.fck_detail
        - Time: span.date (format: "Thứ tư, 12/2/2026, 10:00 (GMT+7)")
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Title
            title_elem = soup.find("h1", class_="title-detail")
            if not title_elem:
                title_elem = soup.find("h1")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Summary
            summary_elem = soup.find("p", class_="description")
            summary = summary_elem.get_text(strip=True) if summary_elem else None
            
            # Content - main article body
            content_elem = soup.find("article", class_="fck_detail")
            if not content_elem:
                content_elem = soup.find("div", class_="fck_detail")
            
            content = ""
            if content_elem:
                paragraphs = []
                for p in content_elem.find_all(["p", "h2", "h3"]):
                    # Skip related articles, captions, etc.
                    if p.find_parent(class_=["box-relatedtop", "box-related"]):
                        continue
                    text = p.get_text(strip=True)
                    if text and not text.startswith("Xem thêm"):
                        paragraphs.append(text)
                content = "\n\n".join(paragraphs)
            
            # Published time
            published_at = None
            date_elem = soup.find("span", class_="date")
            if date_elem:
                time_str = date_elem.get_text(strip=True)
                published_at = self._parse_vnexpress_datetime(time_str)
            
            if not published_at:
                # Try meta tag
                meta_time = soup.find("meta", {"name": "pubdate"})
                if meta_time:
                    time_str = meta_time.get("content", "")
                    published_at = self._parse_vnexpress_datetime(time_str)
            
            if not title:
                return None
            
            return VnExpressArticleContent(
                title=self._clean_text(title),
                url=url,
                content=content,
                summary=self._clean_text(summary) if summary else None,
                published_at=published_at,
            )
            
        except Exception as e:
            logger.error(f"[vnexpress] Error parsing article {url}: {e}")
            return None
    
    async def run(
        self,
        categories: Optional[List[str]] = None,
        max_articles: Optional[int] = None,
        save_raw: bool = False,
        existing_titles: Optional[set] = None,
    ) -> CrawlResult:
        """
        Full crawl: fetch article list + content.
        
        Args:
            categories: List of category slugs to crawl
            max_articles: Limit number of articles to fetch content (None = all)
            save_raw: Save raw data to JSON file for debugging
            existing_titles: Set of titles already in DB (skip fetching content for these)
            
        Returns:
            CrawlResult with articles including content
        """
        logger.info(f"[vnexpress] Starting full crawl (max_articles={max_articles})...")
        
        # Step 1: Fetch article list
        list_result = await self.fetch(categories=categories)
        
        if not list_result.success:
            return list_result
        
        articles = list_result.data
        total_found = len(articles)
        
        # Step 2: Filter out articles already in database
        existing_titles = existing_titles or set()
        new_articles = []
        skipped_count = 0
        
        for article in articles:
            title = (article.get("title") or "").strip()
            if title and title in existing_titles:
                skipped_count += 1
                logger.debug(f"[vnexpress] Skipping duplicate: {title[:50]}...")
                continue
            new_articles.append(article)
        
        if skipped_count > 0:
            logger.info(f"[vnexpress] Skipped {skipped_count} existing articles, {len(new_articles)} new to fetch")
        
        # Step 3: Fetch content for new articles only
        articles_to_fetch = new_articles[:max_articles] if max_articles else new_articles
        fetched_count = 0
        failed_count = 0
        
        logger.info(f"[vnexpress] Fetching content for {len(articles_to_fetch)} articles...")
        
        results = []
        
        for i, item in enumerate(articles, 1):
            if max_articles and i > max_articles:
                # Skip content fetch, keep metadata only
                item["content"] = ""
                results.append(item)
                continue
            
            url = item.get("source_url", "")
            title_short = item.get("title", "")[:50]
            logger.info(f"[vnexpress] [{i}/{len(articles_to_fetch)}] {title_short}...")
            
            article = await self.fetch_article_content(url)
            
            if article:
                # Merge content into item
                item["content"] = article.content
                item["summary"] = article.summary or item.get("summary")
                if article.published_at:
                    item["published_at"] = article.published_at.isoformat()
                fetched_count += 1
            else:
                item["content"] = ""
                failed_count += 1
            
            results.append(item)
            
            # Small delay to be polite
            await asyncio.sleep(0.5)
        
        # Add metadata
        metadata = {
            "type": "metadata",
            "stats": {
                "articles_found": total_found,
                "articles_fetched": fetched_count,
                "articles_failed": failed_count,
            },
            "total_items": len(results),
        }
        
        final_data = [metadata] + results
        
        # Save raw if requested
        if save_raw:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_file = self.data_dir / "raw" / f"vnexpress_{timestamp}.json"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(raw_file, "w", encoding="utf-8") as f:
                json.dump({
                    "source": self.source,
                    "crawled_at": datetime.now().isoformat(),
                    "success": True,
                    "data": final_data,
                    "error": None,
                    "count": len(final_data),
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[vnexpress] Saved raw data to {raw_file}")
        
        logger.info(f"[vnexpress] Crawl complete: {fetched_count}/{total_found} fetched, {failed_count} failed")
        
        return CrawlResult(
            source=self.source,
            crawled_at=datetime.now(),
            success=True,
            data=final_data,
            error=None,
        )
