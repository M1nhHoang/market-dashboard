"""
VnEconomy Crawler - Vietnamese Financial News

Extract news from VnEconomy (https://vneconomy.vn/)

Architecture:
- Crawl homepage to get article list
- Fetch each article for full content + publish date
- Transform to EventRecord for LLM pipeline
"""
import re
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from .base_crawler import BaseCrawler, CrawlResult


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class NewsItem:
    """News item extracted from homepage."""
    title: str
    url: str
    category: Optional[str] = None
    summary: Optional[str] = None
    source: str = "vneconomy"


@dataclass 
class ArticleContent:
    """Full article content."""
    title: str
    url: str
    content: str
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    source: str = "vneconomy"
    
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
# VNECONOMY CRAWLER
# ============================================================

class VnEconomyCrawler(BaseCrawler):
    """
    Crawler for VnEconomy (https://vneconomy.vn/)
    
    Extracts financial/economic news from homepage.
    
    Flow:
    1. fetch() - Get article list from homepage
    2. fetch_article_content() - Get full content per article
    3. run() - Full crawl with content extraction
    """
    
    BASE_URL = "https://vneconomy.vn"
    
    def __init__(self, data_dir: Path):
        super().__init__("vneconomy", data_dir)
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        }
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1.0  # seconds
        
    @property
    def transformer(self):
        """Return the transformer for this crawler."""
        from data_transformers.vneconomy import VnEconomyTransformer
        return VnEconomyTransformer()
        
    async def _rate_limit(self):
        """Ensure minimum interval between requests."""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _make_absolute_url(self, href: str) -> str:
        """Convert relative URL to absolute."""
        if not href:
            return ""
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return f"{self.BASE_URL}{href}"
        return f"{self.BASE_URL}/{href}"
    
    # ============================================================
    # HOMEPAGE EXTRACTION
    # ============================================================
    
    async def fetch(self) -> CrawlResult:
        """
        Fetch article list from VnEconomy homepage.
        
        Returns:
            CrawlResult with list of news items (without full content)
        """
        logger.info(f"[{self.name}] Fetching homepage...")
        
        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                await self._rate_limit()
                response = await client.get(self.BASE_URL, headers=self.headers)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract news items from different sections
            news_items = []
            
            # 1. Featured items (block-highlight section)
            featured = self._extract_featured_items(soup)
            news_items.extend(featured)
            
            # 2. Section items (Tiêu điểm, Chứng khoán, Tài chính, etc.)
            section_items = self._extract_section_items(soup)
            news_items.extend(section_items)
            
            # Deduplicate by URL
            seen_urls = set()
            unique_items = []
            for item in news_items:
                if item.url not in seen_urls:
                    seen_urls.add(item.url)
                    unique_items.append(item)
            
            logger.info(f"[{self.name}] Found {len(unique_items)} unique articles")
            
            return CrawlResult(
                source=self.name,
                crawled_at=datetime.now(),
                success=True,
                data=[{
                    "type": "news",
                    "title": item.title,
                    "source_url": item.url,
                    "category": item.category,
                    "summary": item.summary,
                    "source": item.source,
                } for item in unique_items]
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Homepage fetch error: {e}")
            return CrawlResult(
                source=self.name,
                crawled_at=datetime.now(),
                success=False,
                data=[],
                error=str(e)
            )
    
    def _extract_featured_items(self, soup: BeautifulSoup) -> List[NewsItem]:
        """Extract featured news items from homepage."""
        items = []
        
        # Main featured block
        featured_wrapper = soup.find("div", class_="featured-item_wapper")
        if featured_wrapper:
            # Main featured article
            title_elem = featured_wrapper.find("h3")
            if title_elem:
                link = title_elem.find("a")
                if link:
                    title = link.get("title", "") or link.get_text(strip=True)
                    href = link.get("href", "")
                    
                    # Get category
                    tag = featured_wrapper.find("div", class_="tag-featured")
                    category = tag.find("p", class_="text").get_text(strip=True) if tag else None
                    
                    # Get summary
                    summary_elem = featured_wrapper.find("p", class_="font-vne2")
                    summary = summary_elem.get_text(strip=True) if summary_elem else None
                    
                    if title and href:
                        items.append(NewsItem(
                            title=self._clean_text(title),
                            url=self._make_absolute_url(href),
                            category=self._clean_text(category) if category else None,
                            summary=self._clean_text(summary) if summary else None,
                        ))
        
        # Featured row items
        featured_rows = soup.find_all("div", class_="featured-row_item")
        for row in featured_rows:
            item = self._parse_featured_row_item(row)
            if item:
                items.append(item)
        
        return items
    
    def _extract_section_items(self, soup: BeautifulSoup) -> List[NewsItem]:
        """Extract news from various sections."""
        items = []
        
        # News spotlight sections (Tiêu điểm, Chứng khoán, Tài chính, etc.)
        spotlight_sections = soup.find_all("section", class_="news-spotlight")
        for section in spotlight_sections:
            section_items = self._parse_spotlight_section(section)
            items.extend(section_items)
        
        # Finance section
        finance_section = soup.find("section", class_="news-finance")
        if finance_section:
            items.extend(self._parse_spotlight_section(finance_section))
        
        # Other specific sections
        for section_class in ["news-invest", "news-bds", "news-digital-green"]:
            section = soup.find("section", class_=section_class)
            if section:
                items.extend(self._parse_spotlight_section(section))
        
        return items
    
    def _parse_spotlight_section(self, section) -> List[NewsItem]:
        """Parse a spotlight/news section."""
        items = []
        
        # Featured row items
        featured_rows = section.find_all("div", class_="featured-row_item")
        for row in featured_rows:
            item = self._parse_featured_row_item(row)
            if item:
                items.append(item)
        
        # Spotlight items (sidebar lists)
        spotlight_items = section.find_all("div", class_="new-spotlight_item")
        for sitem in spotlight_items:
            item = self._parse_spotlight_item(sitem)
            if item:
                items.append(item)
        
        return items
    
    def _parse_featured_row_item(self, row) -> Optional[NewsItem]:
        """Parse a featured row item element."""
        try:
            # Find title/link
            title_div = row.find("div", class_="featured-row_item__title")
            if not title_div:
                return None
                
            h3 = title_div.find("h3")
            if not h3:
                return None
            
            title = h3.get("title", "") or h3.get_text(strip=True)
            
            # Find link - could be in h3 or as link-layer-imt
            link = h3.find("a")
            if not link:
                link = row.find("a", class_="link-layer-imt")
            if not link:
                link = row.find("a", class_="responsive-image-link")
            
            if not link:
                return None
                
            href = link.get("href", "")
            if not href or href == "javascript:void(0);":
                return None
            
            # Get category
            tag = row.find("div", class_="tag-featured")
            category = None
            if tag:
                p = tag.find("p", class_="text")
                if p:
                    category = p.get_text(strip=True)
            
            # Get summary (if present)
            summary = None
            p_summary = title_div.find("p")
            if p_summary and not p_summary.find_parent(class_="tag-featured"):
                summary = p_summary.get_text(strip=True)
            
            if title and href:
                return NewsItem(
                    title=self._clean_text(title),
                    url=self._make_absolute_url(href),
                    category=self._clean_text(category) if category else None,
                    summary=self._clean_text(summary) if summary else None,
                )
        except Exception as e:
            logger.debug(f"Error parsing featured row item: {e}")
            
        return None
    
    def _parse_spotlight_item(self, item) -> Optional[NewsItem]:
        """Parse a spotlight sidebar item."""
        try:
            h3 = item.find("h3", class_="name-item")
            if not h3:
                return None
                
            link = h3.find("a")
            if not link:
                return None
                
            title = link.get("title", "") or link.get_text(strip=True)
            href = link.get("href", "")
            
            if not title or not href:
                return None
            
            # Category
            tag = item.find("div", class_="tag-featured")
            category = None
            if tag:
                p = tag.find("p", class_="text")
                if p:
                    category = p.get_text(strip=True)
            
            return NewsItem(
                title=self._clean_text(title),
                url=self._make_absolute_url(href),
                category=self._clean_text(category) if category else None,
            )
        except Exception:
            return None
    
    # ============================================================
    # ARTICLE CONTENT EXTRACTION
    # ============================================================
    
    async def fetch_article_content(self, url: str) -> Optional[ArticleContent]:
        """
        Fetch full article content from article page.
        
        Args:
            url: Article URL
            
        Returns:
            ArticleContent with full text, date, author, etc.
        """
        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                await self._rate_limit()
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract article details
            title = self._extract_article_title(soup)
            content = self._extract_article_content(soup)
            summary = self._extract_article_summary(soup)
            published_at = self._extract_article_date(soup)
            
            return ArticleContent(
                title=title,
                url=url,
                content=content,
                summary=summary,
                published_at=published_at,
                source="vneconomy",
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Error fetching article {url}: {e}")
            return None
    
    def _extract_article_title(self, soup: BeautifulSoup) -> str:
        """Extract article title."""
        # VnEconomy specific: name-detail
        h1 = soup.find("h1", class_="name-detail")
        if h1:
            return h1.get_text(strip=True)
        
        # Fallback: detail-title
        h1 = soup.find("h1", class_="detail-title")
        if h1:
            return h1.get_text(strip=True)
        
        # Fallback to og:title
        og_title = soup.find("meta", property="og:title")
        if og_title:
            return og_title.get("content", "")
        
        return ""
    
    def _extract_article_summary(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article summary/sapo."""
        # VnEconomy specific: sapo-detail
        sapo = soup.find("p", class_="sapo-detail")
        if sapo:
            return sapo.get_text(strip=True)
        
        sapo = soup.find("h2", class_="sapo-detail")
        if sapo:
            return sapo.get_text(strip=True)
        
        # Fallback: detail-sapo
        sapo = soup.find("div", class_="detail-sapo")
        if sapo:
            return sapo.get_text(strip=True)
            
        # og:description as last resort
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            return og_desc.get("content", "")
        
        return None
    
    def _extract_article_content(self, soup: BeautifulSoup) -> str:
        """Extract article main content."""
        content_parts = []
        
        # VnEconomy: Look for block-detail-page section first
        content_div = soup.find("section", class_="block-detail-page")
        if content_div:
            # Get all paragraphs
            for p in content_div.find_all("p"):
                text = p.get_text(strip=True)
                # Filter out short paragraphs and navigation text
                if text and len(text) > 30:
                    # Skip common non-content patterns
                    if text.startswith("VnEconomy cập nhật giá"):
                        continue
                    if "Diễn đàn Kinh tế Việt Nam" in text and len(text) < 100:
                        continue
                    content_parts.append(text)
            
            if content_parts:
                return "\n\n".join(content_parts)
        
        # Fallback: Try other common patterns
        content_div = soup.find("div", class_="detail-content")
        if not content_div:
            content_div = soup.find("div", class_="article-content")
        if not content_div:
            content_div = soup.find("article")
        
        if content_div:
            for p in content_div.find_all("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 30:
                    content_parts.append(text)
        
        return "\n\n".join(content_parts)
    
    def _extract_article_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract article publish date."""
        # Look for date in meta tags
        date_meta = soup.find("meta", property="article:published_time")
        if date_meta:
            try:
                return datetime.fromisoformat(date_meta.get("content", "").replace("Z", "+00:00"))
            except:
                pass
        
        # Look for date in detail-time or similar
        date_elem = soup.find("span", class_="detail-time")
        if not date_elem:
            date_elem = soup.find("div", class_="detail-time")
        if not date_elem:
            date_elem = soup.find("time")
        
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            return self._parse_vietnamese_date(date_text)
        
        return None
    
    def _parse_vietnamese_date(self, date_str: str) -> Optional[datetime]:
        """Parse Vietnamese date format like '14:30 12/02/2026'."""
        if not date_str:
            return None
            
        try:
            # Pattern: HH:MM DD/MM/YYYY or DD/MM/YYYY HH:MM
            patterns = [
                r"(\d{1,2}):(\d{2})\s+(\d{1,2})/(\d{1,2})/(\d{4})",  # HH:MM DD/MM/YYYY
                r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})",  # DD/MM/YYYY HH:MM
                r"(\d{1,2})/(\d{1,2})/(\d{4})",  # DD/MM/YYYY
            ]
            
            for pattern in patterns:
                match = re.search(pattern, date_str)
                if match:
                    groups = match.groups()
                    if len(groups) == 5:
                        if "/" in date_str[:date_str.find(":")]:
                            # DD/MM/YYYY HH:MM
                            day, month, year, hour, minute = groups
                        else:
                            # HH:MM DD/MM/YYYY
                            hour, minute, day, month, year = groups
                        return datetime(int(year), int(month), int(day), int(hour), int(minute))
                    elif len(groups) == 3:
                        day, month, year = groups
                        return datetime(int(year), int(month), int(day))
        except Exception as e:
            logger.debug(f"Error parsing date '{date_str}': {e}")
            
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Decode HTML entities
        text = text.replace('\xa0', ' ')
        return text.strip()
    
    # ============================================================
    # MAIN RUN METHOD
    # ============================================================
    
    async def run(
        self,
        max_articles: Optional[int] = None,
        save_raw: bool = False,
        existing_titles: Optional[set] = None,
    ) -> CrawlResult:
        """
        Run full crawl with content extraction.
        
        Args:
            max_articles: Maximum number of articles to fetch full content.
                         If None, fetch all articles.
            save_raw: If True, save raw data to file.
            existing_titles: Set of titles already in DB (skip fetching content for these)
            
        Returns:
            CrawlResult with all article data
        """
        logger.info(f"[{self.name}] Starting full crawl (max_articles={max_articles})...")
        
        all_data = []
        stats = {
            "articles_found": 0,
            "articles_fetched": 0,
            "articles_failed": 0,
            "articles_skipped": 0,
        }
        
        try:
            # Step 1: Get article list from homepage
            homepage_result = await self.fetch()
            if not homepage_result.success:
                return homepage_result
            
            news_items = homepage_result.data
            stats["articles_found"] = len(news_items)
            
            # Step 2: Filter out articles already in database
            existing_titles = existing_titles or set()
            new_items = []
            
            for item in news_items:
                title = (item.get("title") or "").strip()
                if title and title in existing_titles:
                    stats["articles_skipped"] += 1
                    logger.debug(f"[{self.name}] Skipping duplicate: {title[:50]}...")
                    continue
                new_items.append(item)
            
            if stats["articles_skipped"] > 0:
                logger.info(f"[{self.name}] Skipped {stats['articles_skipped']} existing articles, {len(new_items)} new to fetch")
            
            # Step 3: Fetch full content for new articles only
            items_to_fetch = new_items if max_articles is None else new_items[:max_articles]
            
            logger.info(f"[{self.name}] Fetching content for {len(items_to_fetch)} articles...")
            
            for i, item in enumerate(items_to_fetch, 1):
                url = item.get("source_url", "")
                title = item.get("title", "N/A")
                
                logger.info(f"[{self.name}] [{i}/{len(items_to_fetch)}] {title[:50]}...")
                
                try:
                    article = await self.fetch_article_content(url)
                    
                    if article:
                        # Merge article content with homepage category
                        article_dict = article.to_dict()
                        article_dict["category"] = item.get("category")  # Keep homepage category
                        all_data.append(article_dict)
                        stats["articles_fetched"] += 1
                    else:
                        # Use basic info from homepage
                        all_data.append({
                            **item,
                            "content": "",
                            "fetch_success": False,
                        })
                        stats["articles_failed"] += 1
                        
                except Exception as e:
                    logger.error(f"[{self.name}] Error: {e}")
                    all_data.append({
                        **item,
                        "content": "",
                        "fetch_success": False,
                        "error": str(e),
                    })
                    stats["articles_failed"] += 1
            
            # NOTE: We only return articles that were actually fetched.
            # Articles beyond max_articles or with existing titles are NOT included.
            
            # Add metadata
            all_data.insert(0, {
                "type": "metadata",
                "stats": stats,
                "total_items": len(all_data) - 1,
            })
            
            result = CrawlResult(
                source=self.name,
                crawled_at=datetime.now(),
                success=True,
                data=all_data,
            )
            
            if save_raw:
                self.save_raw(result)
            
            logger.info(
                f"[{self.name}] Crawl complete: "
                f"{stats['articles_fetched']}/{stats['articles_found']} fetched, "
                f"{stats['articles_failed']} failed"
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"[{self.name}] Crawl failed: {e}")
            return CrawlResult(
                source=self.name,
                crawled_at=datetime.now(),
                success=False,
                data=all_data,
                error=str(e),
            )


# ============================================================
# LEGACY NEWS CRAWLER (FOR FUTURE RSS FEEDS)
# ============================================================

class NewsCrawler(BaseCrawler):
    """
    Generic RSS-based news crawler.
    
    Can be extended to support multiple RSS sources.
    Currently not used - VnEconomyCrawler scrapes homepage directly.
    """
    
    def __init__(self, data_dir: Path):
        super().__init__("news", data_dir)
        
        self.rss_feeds = {
            # Add RSS feeds here if needed
            # "cafef": "https://cafef.vn/rss/trang-chu.rss",
            # "vnexpress": "https://vnexpress.net/rss/kinh-doanh.rss",
        }
        
        self.headers = {
            "User-Agent": "MarketIntelligence/1.0"
        }
        
    async def fetch(self) -> CrawlResult:
        """Fetch news from configured RSS feeds."""
        import feedparser
        
        if not self.rss_feeds:
            return CrawlResult(
                source="news",
                crawled_at=datetime.now(),
                success=False,
                data=[],
                error="No RSS feeds configured"
            )
        
        all_articles = []
        errors = []
        
        async with httpx.AsyncClient(timeout=30) as client:
            for source_name, feed_url in self.rss_feeds.items():
                try:
                    response = await client.get(feed_url, headers=self.headers)
                    response.raise_for_status()
                    
                    feed = feedparser.parse(response.text)
                    
                    for entry in feed.entries:
                        all_articles.append({
                            "type": "news",
                            "title": entry.get("title", ""),
                            "source_url": entry.get("link", ""),
                            "summary": self._strip_html(entry.get("summary", "")),
                            "published_at": entry.get("published", ""),
                            "source": source_name,
                        })
                        
                except Exception as e:
                    logger.error(f"[News] Failed to fetch {source_name}: {e}")
                    errors.append(f"{source_name}: {str(e)}")
        
        return CrawlResult(
            source="news",
            crawled_at=datetime.now(),
            success=len(all_articles) > 0,
            data=all_articles,
            error="; ".join(errors) if errors else None
        )
    
    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text(strip=True)
