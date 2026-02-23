"""
Vietcombank Crawler - Commercial exchange rates from Vietcombank

Data source: https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx
Alternative (HTML): https://www.vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich/Ty-gia

Provides commercial buy/sell/transfer exchange rates for ~20 currencies.
These are the actual trading rates (unlike SBV central rate which is reference only).

Key currencies tracked:
- USD, EUR, GBP, JPY, CNY, AUD, SGD, KRW, THB, etc.
"""
import asyncio
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree

import httpx
from loguru import logger

from .base_crawler import BaseCrawler, CrawlResult
from config import settings


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ExchangeRateItem:
    """Single currency exchange rate from Vietcombank."""
    currency_code: str       # e.g., "USD", "EUR"
    currency_name: str       # e.g., "US DOLLAR", "EURO"
    buy: Optional[float]     # Cash buy rate (VND) - may be None for minor currencies
    transfer: Optional[float]  # Transfer buy rate (VND)
    sell: Optional[float]    # Sell rate (VND)
    updated_at: Optional[datetime] = None  # When rates were updated


# Key currencies to track as individual indicators
# Others are still saved but less prominently
KEY_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CNY", "AUD", 
    "SGD", "KRW", "THB", "CAD", "CHF", "HKD",
}


# ============================================================
# VIETCOMBANK CRAWLER
# ============================================================

class VietcombankCrawler(BaseCrawler):
    """
    Crawler for Vietcombank exchange rates.
    
    Uses the official XML API endpoint which returns all currency rates.
    This is more reliable than HTML scraping and officially referenced
    on the Vietcombank website.
    
    Flow:
    1. fetch() - GET XML from API endpoint
    2. Parse XML to ExchangeRateItem list
    3. Return CrawlResult with standardized data format
    """
    
    XML_API_URL = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
    HTML_URL = "https://www.vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich/Ty-gia"
    
    def __init__(self, data_dir: Path):
        super().__init__("vietcombank", data_dir)
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "application/xml, text/xml, */*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        }
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 5.0  # XML API says max 1 request per 5 minutes
        
        # Transformer instance
        self._transformer = None  # Lazy load
    
    @property
    def transformer(self):
        """Return the transformer for this crawler."""
        if self._transformer is None:
            from data_transformers.vietcombank import VietcombankTransformer
            self._transformer = VietcombankTransformer()
        return self._transformer
    
    async def _rate_limit(self):
        """Ensure minimum interval between requests."""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            wait = self._min_request_interval - elapsed
            logger.debug(f"[{self.name}] Rate limiting: waiting {wait:.1f}s")
            await asyncio.sleep(wait)
        self._last_request_time = time.time()
    
    async def fetch(self) -> CrawlResult:
        """
        Fetch exchange rates from Vietcombank XML API.
        
        Returns:
            CrawlResult with exchange rate data items
        """
        logger.info(f"[{self.name}] Fetching exchange rates from XML API...")
        
        all_data = []
        errors = []
        
        try:
            await self._rate_limit()
            
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                verify=settings.CRAWLERS_ENABLE_SSL,
            ) as client:
                response = await client.get(self.XML_API_URL, headers=self.headers)
                response.raise_for_status()
                
                xml_content = response.text
                
                # Parse XML
                rates, updated_at = self._parse_xml(xml_content)
                
                if not rates:
                    return CrawlResult(
                        source=self.name,
                        crawled_at=datetime.now(),
                        success=False,
                        data=[],
                        error="Failed to parse exchange rate XML - no rates found",
                    )
                
                logger.info(f"[{self.name}] Parsed {len(rates)} exchange rates, updated at: {updated_at}")
                
                # Convert to standardized data format
                for rate in rates:
                    data_item = {
                        "type": "exchange_rate",
                        "currency_code": rate.currency_code,
                        "currency_name": rate.currency_name.strip(),
                        "buy": rate.buy,
                        "transfer": rate.transfer,
                        "sell": rate.sell,
                        "unit": "VND",
                        "source": "Vietcombank",
                        "source_url": self.HTML_URL,
                        "updated_at": updated_at.isoformat() if updated_at else None,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "is_key_currency": rate.currency_code in KEY_CURRENCIES,
                    }
                    all_data.append(data_item)
                
                logger.info(
                    f"[{self.name}] Extracted {len(all_data)} exchange rates "
                    f"({sum(1 for d in all_data if d['is_key_currency'])} key currencies)"
                )
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e}"
            logger.error(f"[{self.name}] {error_msg}")
            logger.debug(f"[{self.name}] Response body (first 500 chars): {e.response.text[:500]}")
            errors.append(error_msg)
        except httpx.TimeoutException as e:
            error_msg = f"Request timed out: {e}"
            logger.error(f"[{self.name}] {error_msg}")
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.exception(f"[{self.name}] {error_msg}")  # includes full traceback
            errors.append(error_msg)
        
        # Add metadata as first item
        if all_data:
            metadata = {
                "type": "metadata",
                "category": "crawl_stats",
                "name": "Vietcombank Crawl Statistics",
                "stats": {
                    "total_currencies": len(all_data),
                    "key_currencies": sum(1 for d in all_data if d.get("is_key_currency")),
                },
                "total_items": len(all_data),
            }
            all_data.insert(0, metadata)
        
        return CrawlResult(
            source=self.name,
            crawled_at=datetime.now(),
            success=len(all_data) > 0,
            data=all_data,
            error="; ".join(errors) if errors else None,
        )
    
    def _parse_xml(self, xml_content: str) -> tuple[list[ExchangeRateItem], Optional[datetime]]:
        """
        Parse Vietcombank XML exchange rate response.
        
        XML format:
        <ExrateList>
            <DateTime>2/23/2026 10:33:40 PM</DateTime>
            <Exrate CurrencyCode="USD" CurrencyName="US DOLLAR"
                    Buy="25,880.00" Transfer="25,910.00" Sell="26,290.00" />
            ...
            <Source>Joint Stock Commercial Bank...</Source>
        </ExrateList>
        
        Returns:
            Tuple of (list of ExchangeRateItem, update datetime)
        """
        rates = []
        updated_at = None
        
        try:
            # Clean XML - remove the comment line if present
            xml_clean = re.sub(r'<!--.*?-->', '', xml_content)
            logger.debug(f"[{self.name}] Parsing XML ({len(xml_clean)} chars)")
            root = ElementTree.fromstring(xml_clean.strip())
            
            # Parse DateTime
            dt_element = root.find("DateTime")
            if dt_element is not None and dt_element.text:
                updated_at = self._parse_vcb_datetime(dt_element.text.strip())
                logger.debug(f"[{self.name}] Rate timestamp from XML: {dt_element.text.strip()} → {updated_at}")
            
            # Parse each Exrate element
            for exrate in root.findall("Exrate"):
                currency_code = exrate.get("CurrencyCode", "")
                currency_name = exrate.get("CurrencyName", "")
                
                buy = self._parse_rate_value(exrate.get("Buy", ""))
                transfer = self._parse_rate_value(exrate.get("Transfer", ""))
                sell = self._parse_rate_value(exrate.get("Sell", ""))
                
                if currency_code and (buy is not None or transfer is not None or sell is not None):
                    rates.append(ExchangeRateItem(
                        currency_code=currency_code,
                        currency_name=currency_name,
                        buy=buy,
                        transfer=transfer,
                        sell=sell,
                        updated_at=updated_at,
                    ))
                    logger.debug(f"[{self.name}] {currency_code}: buy={buy}, transfer={transfer}, sell={sell}")
                else:
                    logger.debug(f"[{self.name}] Skipped {currency_code!r} (no valid rates)")
                    
        except ElementTree.ParseError as e:
            logger.error(f"[{self.name}] XML parse error: {e}")
            logger.debug(f"[{self.name}] Raw XML (first 300 chars): {xml_content[:300]}")
        except Exception as e:
            logger.exception(f"[{self.name}] Error parsing XML: {e}")  # full traceback
        
        return rates, updated_at
    
    @staticmethod
    def _parse_rate_value(value_str: str) -> Optional[float]:
        """
        Parse a rate value string like '25,880.00' or '-' to float.
        
        Returns None if value is '-' or unparseable.
        """
        if not value_str or value_str.strip() == "-":
            return None
        try:
            # Remove commas: "25,880.00" → "25880.00"
            cleaned = value_str.strip().replace(",", "")
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _parse_vcb_datetime(dt_str: str) -> Optional[datetime]:
        """
        Parse Vietcombank datetime format.
        
        Format: "2/23/2026 10:33:40 PM"
        """
        try:
            return datetime.strptime(dt_str, "%m/%d/%Y %I:%M:%S %p")
        except (ValueError, TypeError):
            try:
                # Try without AM/PM
                return datetime.strptime(dt_str, "%m/%d/%Y %H:%M:%S")
            except (ValueError, TypeError):
                logger.warning(f"Could not parse VCB datetime: {dt_str}")
                return None
    
    async def run(
        self,
        save_raw: bool = False,
        existing_titles: Optional[set] = None,
    ) -> CrawlResult:
        """
        Run the Vietcombank crawler.
        
        This crawler only produces metrics (no news/events), so the run method 
        is simpler than news crawlers.
        
        Args:
            save_raw: If True, save raw data to file for debugging.
            existing_titles: Not used (no news articles), kept for interface compat.
            
        Returns:
            CrawlResult with exchange rate data
        """
        logger.info(f"[{self.name}] Starting exchange rate crawl...")
        
        try:
            result = await self.fetch()
            
            if result.success:
                logger.info(f"[{self.name}] Successfully crawled {len(result.data)} items")
                
                if save_raw:
                    self.save_raw(result)
                
                # Transform and save
                if self.transformer is not None:
                    output = self.transformer.transform(result.to_dict())
                    self.save_transformed(output)
                    logger.info(f"[{self.name}] Transformed: {output.summary()}")
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
                error=str(e),
            )
