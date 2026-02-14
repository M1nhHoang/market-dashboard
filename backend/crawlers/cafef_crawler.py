"""
CafeF Crawler - Vietnamese Financial News

Extract news from CafeF (https://cafef.vn/)

Categories to crawl:
- /thi-truong-chung-khoan.chn - Chứng khoán (Stock market)
- /tai-chinh-ngan-hang.chn - Ngân hàng (Banking)
- /vi-mo-dau-tu.chn - Vĩ mô (Macro)
- /tai-chinh-quoc-te.chn - Tài chính quốc tế (International finance)

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
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from .base_crawler import BaseCrawler, CrawlResult
from data_transformers.cafef import CafeFTransformer


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class CafeFNewsItem:
    """News item extracted from CafeF category page."""
    title: str
    url: str
    category: Optional[str] = None
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    source: str = "cafef"


@dataclass 
class CafeFArticleContent:
    """Full article content from CafeF."""
    title: str
    url: str
    content: str
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    source: str = "cafef"
    
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
# CAFEF CRAWLER
# ============================================================

class CafeFCrawler(BaseCrawler):
    """
    Crawler for CafeF (https://cafef.vn/)
    
    Crawls category pages to extract news articles.
    
    Categories:
    - thi-truong-chung-khoan: Chứng khoán (Stock market)
    - tai-chinh-ngan-hang: Ngân hàng (Banking)
    - vi-mo-dau-tu: Vĩ mô (Macro)
    - tai-chinh-quoc-te: Tài chính quốc tế (International)
    
    Flow:
    1. fetch() - Get article list from category pages
    2. fetch_article_content() - Get full content per article
    3. run() - Full crawl with content extraction
    """
    
    BASE_URL = "https://cafef.vn"
    
    # Category URLs to crawl with their display names
    CATEGORIES = {
        "thi-truong-chung-khoan": "Chứng khoán",
        "tai-chinh-ngan-hang": "Ngân hàng",
        "vi-mo-dau-tu": "Vĩ mô",
        "tai-chinh-quoc-te": "Tài chính quốc tế",
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
        super().__init__(name="cafef", data_dir=data_dir)
        self.source = "cafef"
        self._transformer = CafeFTransformer()
    
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
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _parse_cafef_datetime(self, time_str: str) -> Optional[datetime]:
        """
        Parse CafeF datetime formats.
        
        Formats:
        - ISO: "2026-02-12T14:19:00"
        - Display: "12/02/2026 - 00:05"
        """
        if not time_str:
            return None
        
        time_str = time_str.strip()
        
        # Try ISO format first (from time-ago title attribute)
        try:
            return datetime.fromisoformat(time_str)
        except ValueError:
            pass
        
        # Try display format: "12/02/2026 - 00:05"
        try:
            # Remove the separator and parse
            clean = time_str.replace(" - ", " ")
            return datetime.strptime(clean, "%d/%m/%Y %H:%M")
        except ValueError:
            pass
        
        return None
    
    async def fetch(self, categories: Optional[List[str]] = None) -> CrawlResult:
        """
        Fetch article list from CafeF category pages.
        
        Args:
            categories: List of category slugs to crawl. 
                        Default: all defined categories.
        
        Returns:
            CrawlResult with list of news items (no full content yet)
        """
        if categories is None:
            categories = list(self.CATEGORIES.keys())
        
        all_items: List[CafeFNewsItem] = []
        
        async with httpx.AsyncClient(
            timeout=30.0, 
            headers=self.HEADERS,
            verify=False,  # CafeF sometimes has SSL issues
            follow_redirects=True,
        ) as client:
            for cat_slug in categories:
                cat_name = self.CATEGORIES.get(cat_slug, cat_slug)
                url = f"{self.BASE_URL}/{cat_slug}.chn"
                
                logger.info(f"[cafef] Fetching {cat_name}: {url}")
                
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    items = self._parse_category_page(
                        response.text, 
                        category=cat_name
                    )
                    all_items.extend(items)
                    logger.info(f"[cafef] Found {len(items)} articles in {cat_name}")
                    
                except Exception as e:
                    logger.error(f"[cafef] Error fetching {cat_name}: {e}")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_items = []
        for item in all_items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)
        
        logger.info(f"[cafef] Found {len(unique_items)} unique articles")
        
        return CrawlResult(
            source=self.source,
            crawled_at=datetime.now(),
            success=True,
            data=[self._item_to_dict(item) for item in unique_items],
            error=None,
        )
    
    def _item_to_dict(self, item: CafeFNewsItem) -> Dict[str, Any]:
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
    
    def _parse_category_page(self, html: str, category: str) -> List[CafeFNewsItem]:
        """
        Parse CafeF category page HTML.
        
        Extracts articles from:
        - Featured items (.firstitem)
        - Secondary featured (.cate-hl-row2 .big)
        - News list (.tlitem)
        """
        soup = BeautifulSoup(html, "html.parser")
        items: List[CafeFNewsItem] = []
        
        # 1. Parse featured item (.firstitem)
        firstitem = soup.find("div", class_="firstitem")
        if firstitem:
            item = self._parse_firstitem(firstitem, category)
            if item:
                items.append(item)
        
        # 2. Parse secondary featured (.cate-hl-row2 .big)
        row2 = soup.find("div", class_="cate-hl-row2")
        if row2:
            for big in row2.find_all("div", class_="big"):
                item = self._parse_big_item(big, category)
                if item:
                    items.append(item)
        
        # 3. Parse news list items (.tlitem)
        for tlitem in soup.find_all("div", class_="tlitem"):
            item = self._parse_tlitem(tlitem, category)
            if item:
                items.append(item)
        
        return items
    
    def _parse_firstitem(self, elem, category: str) -> Optional[CafeFNewsItem]:
        """Parse featured first item."""
        try:
            # Title and URL from h2 > a
            h2 = elem.find("h2")
            if not h2:
                return None
            
            link = h2.find("a")
            if not link:
                return None
            
            title = link.get("title", "") or link.get_text(strip=True)
            href = link.get("href", "")
            
            if not title or not href:
                return None
            
            # Summary from .sapo
            sapo = elem.find("p", class_="sapo")
            summary = sapo.get_text(strip=True) if sapo else None
            
            # Time from .time
            time_elem = elem.find("p", class_="time")
            published_at = None
            if time_elem:
                time_str = time_elem.get("data-time") or time_elem.get_text(strip=True)
                published_at = self._parse_cafef_datetime(time_str)
            
            return CafeFNewsItem(
                title=self._clean_text(title),
                url=self._make_absolute_url(href),
                category=category,
                summary=self._clean_text(summary) if summary else None,
                published_at=published_at,
            )
        except Exception:
            return None
    
    def _parse_big_item(self, elem, category: str) -> Optional[CafeFNewsItem]:
        """Parse secondary featured item (.big)."""
        try:
            # Title and URL from h3 > a
            h3 = elem.find("h3")
            if not h3:
                return None
            
            link = h3.find("a")
            if not link:
                return None
            
            title = link.get("title", "") or link.get_text(strip=True)
            href = link.get("href", "")
            
            if not title or not href:
                return None
            
            # Summary from .sapo (usually hidden)
            sapo = elem.find("p", class_="sapo")
            summary = sapo.get_text(strip=True) if sapo else None
            
            # Time from .time
            time_elem = elem.find("p", class_="time")
            published_at = None
            if time_elem:
                time_str = time_elem.get("data-time") or time_elem.get_text(strip=True)
                published_at = self._parse_cafef_datetime(time_str)
            
            return CafeFNewsItem(
                title=self._clean_text(title),
                url=self._make_absolute_url(href),
                category=category,
                summary=self._clean_text(summary) if summary else None,
                published_at=published_at,
            )
        except Exception:
            return None
    
    def _parse_tlitem(self, elem, category: str) -> Optional[CafeFNewsItem]:
        """Parse news list item (.tlitem)."""
        try:
            # Title and URL from h3 > a
            h3 = elem.find("h3")
            if not h3:
                return None
            
            link = h3.find("a")
            if not link:
                return None
            
            title = link.get_text(strip=True)
            href = link.get("href", "")
            
            if not title or not href:
                return None
            
            # Summary from .sapo
            sapo = elem.find("p", class_="sapo")
            summary = sapo.get_text(strip=True) if sapo else None
            
            # Time from .time-ago (ISO in title) or .time
            published_at = None
            time_elem = elem.find("span", class_="time-ago")
            if time_elem:
                time_str = time_elem.get("title", "")
                published_at = self._parse_cafef_datetime(time_str)
            else:
                time_elem = elem.find(class_="time")
                if time_elem:
                    time_str = time_elem.get("data-time") or time_elem.get_text(strip=True)
                    published_at = self._parse_cafef_datetime(time_str)
            
            return CafeFNewsItem(
                title=self._clean_text(title),
                url=self._make_absolute_url(href),
                category=category,
                summary=self._clean_text(summary) if summary else None,
                published_at=published_at,
            )
        except Exception:
            return None
    
    async def fetch_article_content(self, url: str) -> Optional[CafeFArticleContent]:
        """
        Fetch full content from a CafeF article URL.
        
        Args:
            url: Full URL to the article
            
        Returns:
            CafeFArticleContent or None if failed
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
            logger.error(f"[cafef] Error fetching article {url}: {e}")
            return None
    
    def _parse_article_page(self, html: str, url: str) -> Optional[CafeFArticleContent]:
        """
        Parse CafeF article page.
        
        Article structure:
        - Title: h1.title-detail
        - Summary: p.sapo
        - Content: div.detail-content
        - Time: span.pdate (format: "12-02-2026 - 14:19 PM")
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Title
            title_elem = soup.find("h1", class_="title-detail")
            if not title_elem:
                # Try alternative selector
                title_elem = soup.find("h1")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Summary
            summary_elem = soup.find("p", class_="sapo")
            summary = summary_elem.get_text(strip=True) if summary_elem else None
            
            # Content
            content_elem = soup.find("div", class_="detail-content")
            if not content_elem:
                # Try alternative
                content_elem = soup.find("div", class_="contentdetail")
            
            content = ""
            if content_elem:
                # Get text from paragraphs
                paragraphs = []
                for p in content_elem.find_all(["p", "h2", "h3"]):
                    text = p.get_text(strip=True)
                    if text and not text.startswith("Xem thêm"):
                        paragraphs.append(text)
                content = "\n\n".join(paragraphs)
            
            # Published time
            published_at = None
            time_elem = soup.find("span", class_="pdate")
            if time_elem:
                time_str = time_elem.get_text(strip=True)
                published_at = self._parse_article_datetime(time_str)
            
            if not title:
                return None
            
            return CafeFArticleContent(
                title=self._clean_text(title),
                url=url,
                content=content,
                summary=self._clean_text(summary) if summary else None,
                published_at=published_at,
            )
            
        except Exception as e:
            logger.error(f"[cafef] Error parsing article {url}: {e}")
            return None
    
    def _parse_article_datetime(self, time_str: str) -> Optional[datetime]:
        """
        Parse article page datetime.
        
        Format: "12-02-2026 - 14:19 PM" or similar
        """
        if not time_str:
            return None
        
        # Clean up
        time_str = time_str.strip()
        time_str = re.sub(r'\s*(AM|PM)\s*', '', time_str, flags=re.IGNORECASE)
        time_str = time_str.replace(" - ", " ")
        
        # Try various formats
        formats = [
            "%d-%m-%Y %H:%M",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d %H:%M",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue
        
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
        logger.info(f"[cafef] Starting full crawl (max_articles={max_articles})...")
        
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
                logger.debug(f"[cafef] Skipping duplicate: {title[:50]}...")
                continue
            new_articles.append(article)
        
        if skipped_count > 0:
            logger.info(f"[cafef] Skipped {skipped_count} existing articles, {len(new_articles)} new to fetch")
        
        # Step 3: Fetch content for new articles only
        articles_to_fetch = new_articles[:max_articles] if max_articles else new_articles
        fetched_count = 0
        failed_count = 0
        
        logger.info(f"[cafef] Fetching content for {len(articles_to_fetch)} articles...")
        
        results = []
        
        for i, item in enumerate(articles_to_fetch, 1):
            url = item.get("source_url", "")
            title_short = item.get("title", "")[:50]
            logger.info(f"[cafef] [{i}/{len(articles_to_fetch)}] {title_short}...")
            
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
            raw_file = self.data_dir / "raw" / f"cafef_{timestamp}.json"
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
            
            logger.info(f"[cafef] Saved raw data to {raw_file}")
        
        logger.info(f"[cafef] Crawl complete: {fetched_count}/{total_found} fetched, {failed_count} failed")
        
        return CrawlResult(
            source=self.source,
            crawled_at=datetime.now(),
            success=True,
            data=final_data,
            error=None,
        )
