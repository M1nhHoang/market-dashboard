"""
SBV Crawler - Vietnam Central Bank data (Ngân hàng Nhà nước Việt Nam)

Data sources from https://www.sbv.gov.vn:
- Tỷ giá trung tâm USD/VND (Central exchange rate)
- Dư nợ tín dụng (Credit balance) 
- Cán cân thanh toán quốc tế (Balance of payments)
- Tin tức & Sự kiện (News & Events)
- Thông cáo báo chí (Press releases)
- Văn bản QPPL (Legal documents)
"""
import asyncio
import re
import json
import io
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from bs4 import BeautifulSoup

import httpx
from loguru import logger

# PDF extraction
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("[SBV] PyMuPDF not installed. PDF text extraction disabled. Install with: pip install pymupdf")

from .base_crawler import BaseCrawler, CrawlResult, IndicatorData
from data_transformers.sbv import SBVTransformer
from config import settings


@dataclass
class ExchangeRateData:
    """Exchange rate data structure."""
    date: str
    central_rate: float  # Tỷ giá trung tâm USD/VND
    source_url: str


@dataclass
class CreditData:
    """Credit balance data structure."""
    date: str
    value: float  # Dư nợ tín dụng (tỷ đồng or % YoY)
    unit: str
    source_url: str


@dataclass
class GoldPriceData:
    """Gold price data structure."""
    organization: str  # tenToChuc - Tổ chức niêm yết
    gold_type: str  # loaiVang - Loại vàng (SJC, VRTL 999.9, etc.)
    buy_price: float  # giaMuaNiemYet - Giá mua
    sell_price: float  # giaBanNiemYet - Giá bán
    weight_unit: str  # khoiLuong - Đơn vị khối lượng (1 Lượng, 1 chỉ)
    price_unit: str  # donViTinh - Đơn vị giá (VND/lượng, VNĐ/chỉ)
    date: str  # ngayDuLieu
    updated_at: str  # ngayCapNhat
    source: str  # Bank code (SJC, TPBank, BaoTinMinhChau)
    source_url: str


@dataclass
class PolicyRateData:
    """SBV policy interest rate data (Lãi suất NHNN quy định)."""
    rate_type: str  # Loại lãi suất (tái chiết khấu, tái cấp vốn)
    value: float  # Giá trị (%)
    decision: str  # Văn bản quyết định
    effective_date: str  # Ngày áp dụng
    source_url: str


@dataclass 
class InterbankRateData:
    """Interbank market interest rate data (Lãi suất thị trường liên ngân hàng)."""
    term: str  # Thời hạn (Qua đêm, 1 Tuần, 2 Tuần, 1 Tháng, 3 Tháng, 6 Tháng, 9 Tháng)
    avg_rate: float  # Lãi suất BQ liên Ngân hàng (% năm)
    volume: float  # Doanh số (Tỷ đồng)
    date: str  # Ngày áp dụng
    note: Optional[str] = None  # Ghi chú (nếu có)
    source_url: str = ""


@dataclass
class CPIData:
    """
    Consumer Price Index data (Chỉ số giá tiêu dùng).
    
    Data is published monthly by General Statistics Office (Tổng cục Thống kê)
    and reported on SBV website.
    """
    title: str  # Tiêu đề bài viết
    month: int  # Tháng
    year: int  # Năm
    mom_change: float  # % thay đổi so với tháng trước (Month-over-Month)
    ytd_change: Optional[float] = None  # % thay đổi so với tháng 12 năm trước (Year-to-Date)
    yoy_change: Optional[float] = None  # % thay đổi so với cùng kỳ năm trước (Year-over-Year)
    core_inflation: Optional[float] = None  # Lạm phát cơ bản (%)
    summary: Optional[str] = None  # Tóm tắt nội dung
    publish_date: str = ""  # Ngày công bố
    source_url: str = ""


@dataclass
class OMOData:
    """
    Open Market Operations data (Nghiệp vụ thị trường mở).
    
    OMO is the main monetary policy tool of SBV to manage liquidity in the banking system.
    SBV conducts repo/reverse repo transactions with commercial banks.
    
    Transaction types:
    - Mua kỳ hạn (Repo): SBV buys securities with agreement to sell back (inject liquidity)
    - Bán kỳ hạn (Reverse Repo): SBV sells securities with agreement to buy back (withdraw liquidity)
    
    Note: Multiple auction rounds can occur on the same day. Each group header 
    (e.g., "Mua kỳ hạn") in the table represents a separate auction round.
    """
    transaction_type: str  # Loại hình giao dịch (Mua kỳ hạn, Bán kỳ hạn)
    auction_round: int  # Phiên đấu thầu trong ngày (1, 2, 3, ...)
    term: str  # Kỳ hạn (7 ngày, 28 ngày, 56 ngày, etc.)
    participants: str  # Số thành viên tham gia/trúng thầu (e.g., "13/13")
    volume: float  # Khối lượng trúng thầu (Tỷ đồng)
    interest_rate: float  # Lãi suất trúng thầu (%/năm)
    date: str  # Ngày đấu thầu
    is_total: bool = False  # True if this is a subtotal row
    source_url: str = ""


@dataclass
class NewsItem:
    """News/Press release item."""
    title: str
    url: str
    date: Optional[str] = None
    summary: Optional[str] = None
    category: str = "news"  # news, press_release, legal


class SBVCrawler(BaseCrawler):
    """
    Crawler for State Bank of Vietnam (Ngân hàng Nhà nước Việt Nam).
    
    Extracts data from https://www.sbv.gov.vn including:
    - Exchange rates (tỷ giá trung tâm)
    - Credit statistics
    - News and press releases with PDF attachments
    """
    
    def __init__(self, data_dir):
        super().__init__("sbv", data_dir)
        
        self.base_url = "https://www.sbv.gov.vn"
        # NOTE: Old SBV gold price API is deprecated (returns 404)
        # Now using SJC direct API instead
        self.gold_price_api = "https://sjc.com.vn/GoldPrice/Services/PriceService.ashx"
        self.interest_rate_url = "https://www.sbv.gov.vn/vi/lãi-suất1"
        self.cpi_url = "https://www.sbv.gov.vn/vi/cpi"
        self.omo_url = "https://sbv.gov.vn/vi/nghiệp-vụ-thị-trường-mở"
        
        # Gold price sources - now only SJC (other sources deprecated)
        # Old: ["SJC", "TPBank", "BaoTinMinhChau"] via SBV API
        self.gold_price_banks = ["SJC"]
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        
        # Rate limiting
        self._last_request = 0
        self._min_interval = 2.0  # seconds between requests
        
        # Transformer instance
        self._transformer = SBVTransformer()
    
    @property
    def transformer(self) -> SBVTransformer:
        """Return the SBV transformer instance."""
        return self._transformer
        
    async def _rate_limit(self):
        """Ensure minimum interval between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request = asyncio.get_event_loop().time()

    def _make_absolute_url(self, href: str) -> str:
        """Convert relative URL to absolute URL."""
        if not href:
            return ""
        if href.startswith('/'):
            return f"{self.base_url}{href}"
        elif not href.startswith('http'):
            return f"{self.base_url}/{href}"
        return href
        
    async def fetch(self) -> CrawlResult:
        """
        Fetch all SBV data from homepage.
        
        Returns:
            CrawlResult with exchange rates, news, and other data
        """
        logger.info("[SBV] Starting fetch from sbv.gov.vn")
        
        all_data = []
        errors = []
        
        try:
            await self._rate_limit()
            
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                verify=settings.CRAWLERS_ENABLE_SSL
            ) as client:
                response = await client.get(self.base_url, headers=self.headers)
                response.raise_for_status()
                html_content = response.text
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract exchange rate
                exchange_rate = self._extract_exchange_rate(html_content)
                if exchange_rate:
                    all_data.append({
                        "name": "USD/VND Central Rate",
                        "value": exchange_rate.central_rate,
                        "unit": "VND",
                        "date": exchange_rate.date,
                        "source": "SBV",
                        "source_url": exchange_rate.source_url,
                        "type": "exchange_rate",
                        "category": "forex"
                    })
                    logger.info(f"[SBV] Extracted exchange rate: {exchange_rate.central_rate}")
                
                # Extract credit data
                credit_data = self._extract_credit_data(html_content)
                if credit_data:
                    for cd in credit_data:
                        all_data.append({
                            "name": "Dư nợ tín dụng",
                            "value": cd.value,
                            "unit": cd.unit,
                            "date": cd.date,
                            "source": "SBV",
                            "source_url": cd.source_url,
                            "type": "credit",
                            "category": "credit"
                        })
                    logger.info(f"[SBV] Extracted {len(credit_data)} credit data points")
                
                # Extract gold prices from API
                gold_prices = await self._fetch_gold_prices(client)
                if gold_prices:
                    for gp in gold_prices:
                        all_data.append({
                            "name": f"Giá vàng {gp.gold_type}",
                            "organization": gp.organization,
                            "gold_type": gp.gold_type,
                            "buy_price": gp.buy_price,
                            "sell_price": gp.sell_price,
                            "weight_unit": gp.weight_unit,
                            "price_unit": gp.price_unit,
                            "date": gp.date,
                            "updated_at": gp.updated_at,
                            "source": f"SBV/{gp.source}",
                            "source_url": gp.source_url,
                            "type": "gold_price",
                            "category": "commodity"
                        })
                    logger.info(f"[SBV] Extracted {len(gold_prices)} gold price items")
                
                # Extract interest rates (policy rates and interbank rates)
                policy_rates, interbank_rates = await self._fetch_interest_rates(client)
                
                if policy_rates:
                    for pr in policy_rates:
                        all_data.append({
                            "name": f"Lãi suất {pr.rate_type}",
                            "rate_type": pr.rate_type,
                            "value": pr.value,
                            "unit": "%",
                            "decision": pr.decision,
                            "effective_date": pr.effective_date,
                            "source": "SBV",
                            "source_url": pr.source_url,
                            "type": "policy_rate",
                            "category": "interest_rate"
                        })
                    logger.info(f"[SBV] Extracted {len(policy_rates)} policy rates")
                
                if interbank_rates:
                    for ir in interbank_rates:
                        all_data.append({
                            "name": f"Lãi suất liên ngân hàng {ir.term}",
                            "term": ir.term,
                            "avg_rate": ir.avg_rate,
                            "volume": ir.volume,
                            "unit_rate": "% năm",
                            "unit_volume": "Tỷ đồng",
                            "date": ir.date,
                            "note": ir.note,
                            "source": "SBV",
                            "source_url": ir.source_url,
                            "type": "interbank_rate",
                            "category": "interest_rate"
                        })
                    logger.info(f"[SBV] Extracted {len(interbank_rates)} interbank rates")
                
                # Extract CPI data
                cpi_data = await self._fetch_cpi(client)
                if cpi_data:
                    for cpi in cpi_data:
                        all_data.append({
                            "name": f"CPI {cpi.month}/{cpi.year}",
                            "value": cpi.mom_change,
                            "unit": "%",
                            "date": cpi.publish_date or f"{cpi.year}-{cpi.month:02d}-01",
                            "source": "SBV/GSO",
                            "source_url": cpi.source_url,
                            "type": "cpi",
                            "category": "inflation",
                            "month": cpi.month,
                            "year": cpi.year,
                            "mom_change": cpi.mom_change,
                            "ytd_change": cpi.ytd_change,
                            "yoy_change": cpi.yoy_change,
                            "core_inflation": cpi.core_inflation,
                            "title": cpi.title,
                            "summary": cpi.summary
                        })
                    logger.info(f"[SBV] Extracted {len(cpi_data)} CPI data points")
                
                # Extract OMO data
                omo_data = await self._fetch_omo(client)
                if omo_data:
                    for omo in omo_data:
                        all_data.append({
                            "name": f"OMO {omo.transaction_type} Phiên {omo.auction_round} {omo.term}",
                            "transaction_type": omo.transaction_type,
                            "auction_round": omo.auction_round,
                            "term": omo.term,
                            "participants": omo.participants,
                            "volume": omo.volume,
                            "interest_rate": omo.interest_rate,
                            "unit_volume": "Tỷ đồng",
                            "unit_rate": "% năm",
                            "date": omo.date,
                            "is_total": omo.is_total,
                            "source": "SBV",
                            "source_url": omo.source_url,
                            "type": "omo",
                            "category": "monetary_policy"
                        })
                    logger.info(f"[SBV] Extracted {len(omo_data)} OMO data points")
                
                # Extract news
                news_items = self._extract_news(soup)
                logger.info(f"[SBV] Extracted {len(news_items)} news items")
                
                # Extract press releases
                press_releases = self._extract_press_releases(soup)
                logger.info(f"[SBV] Extracted {len(press_releases)} press releases")
                
                # Convert news to dict format for unified storage
                for item in news_items + press_releases:
                    all_data.append({
                        "name": f"SBV {item.category}",
                        "value": 0,
                        "unit": "text",
                        "date": item.date or datetime.now().strftime("%Y-%m-%d"),
                        "source": "SBV",
                        "source_url": item.url,
                        "type": item.category,
                        "category": "news",
                        "title": item.title,
                        "summary": item.summary
                    })
                    
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {str(e)}"
            logger.error(f"[SBV] {error_msg}")
            errors.append(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(f"[SBV] {error_msg}")
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(f"[SBV] {error_msg}")
            errors.append(error_msg)
            
        return CrawlResult(
            source="sbv",
            crawled_at=datetime.now(),
            success=len(all_data) > 0,
            data=all_data,
            error="; ".join(errors) if errors else None
        )
    
    # ============================================================
    # HOMEPAGE DATA EXTRACTION
    # ============================================================
    
    def _extract_exchange_rate(self, html_content: str) -> Optional[ExchangeRateData]:
        """
        Extract USD/VND central exchange rate from JavaScript in page.
        
        The rate is embedded in JavaScript like:
        var tyGiaValues = [25099, 25099, 25099, 25099, ...];
        var dates = ["21-10-2025", "22-10-2025", ...];
        """
        try:
            rate_match = re.search(r'var\s+tyGiaValues\s*=\s*\[([\d,\s]+)\]', html_content)
            date_match = re.search(r'var\s+dates\s*=\s*\[(.*?)\]', html_content, re.DOTALL)
            
            if rate_match and date_match:
                rates = [float(r.strip()) for r in rate_match.group(1).split(',') if r.strip()]
                dates = re.findall(r'"([^"]+)"', date_match.group(1))
                
                if rates and dates:
                    latest_rate = rates[-1]
                    latest_date = dates[-1] if dates else datetime.now().strftime("%d-%m-%Y")
                    
                    try:
                        dt = datetime.strptime(latest_date, "%d-%m-%Y")
                        formatted_date = dt.strftime("%Y-%m-%d")
                    except:
                        formatted_date = latest_date
                    
                    return ExchangeRateData(
                        date=formatted_date,
                        central_rate=latest_rate,
                        source_url=self.base_url
                    )
                    
            logger.warning("[SBV] Could not find exchange rate data in JavaScript")
            return None
            
        except Exception as e:
            logger.error(f"[SBV] Error extracting exchange rate: {e}")
            return None
    
    def _extract_credit_data(self, html_content: str) -> List[CreditData]:
        """Extract credit balance data from JavaScript charts."""
        credit_data = []
        
        try:
            values_match = re.search(r'var\s+ChartDuNoValues\s*=\s*\[(.*?)\]', html_content, re.DOTALL)
            labels_match = re.search(r'var\s+ChartDuNoLabels\s*=\s*\[(.*?)\]', html_content, re.DOTALL)
            
            if values_match and labels_match:
                values = re.findall(r'"([^"]+)"', values_match.group(1))
                labels = re.findall(r'"([^"]+)"', labels_match.group(1))
                
                for value, label in zip(values, labels):
                    try:
                        credit_data.append(CreditData(
                            date=label,
                            value=float(value),
                            unit="% YoY",
                            source_url=self.base_url
                        ))
                    except ValueError:
                        continue
                        
        except Exception as e:
            logger.error(f"[SBV] Error extracting credit data: {e}")
            
        return credit_data
    
    async def _fetch_gold_prices(
        self, 
        client: httpx.AsyncClient,
        banks: Optional[List[str]] = None
    ) -> List[GoldPriceData]:
        """
        Fetch gold prices from SJC API.
        
        NOTE: Old SBV API deprecated. Now fetching directly from SJC.
        
        Args:
            client: httpx AsyncClient instance
            banks: Ignored (kept for backward compatibility)
        
        Returns:
            List of GoldPriceData objects
        """
        gold_prices = []
        
        try:
            await self._rate_limit()
            
            url = self.gold_price_api
            logger.info(f"[SBV] Fetching gold prices from SJC...")
            
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Check for empty response
            if not response.text or response.text.strip() == '':
                logger.warning(f"[SBV] Gold price API returned empty response")
                return gold_prices
            
            # Parse JSON response
            try:
                data = response.json()
            except Exception as json_err:
                logger.error(f"[SBV] Failed to parse gold price JSON: {json_err}")
                return gold_prices
            
            if not data.get("success"):
                logger.warning(f"[SBV] Gold price API returned non-success")
                return gold_prices
            
            # Parse date from "HH:MM DD/MM/YYYY" format
            latest_date_str = data.get("latestDate", "")
            try:
                # Format: "08:21 14/02/2026"
                dt = datetime.strptime(latest_date_str, "%H:%M %d/%m/%Y")
                formatted_date = dt.strftime("%Y-%m-%d")
                formatted_updated = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                formatted_date = datetime.now().strftime("%Y-%m-%d")
                formatted_updated = formatted_date
            
            items = data.get("data", [])
            
            for item in items:
                try:
                    gold_prices.append(GoldPriceData(
                        organization=item.get("BranchName", ""),
                        gold_type=item.get("TypeName", ""),
                        buy_price=float(item.get("BuyValue", 0)),
                        sell_price=float(item.get("SellValue", 0)),
                        weight_unit="lượng",
                        price_unit="VND",
                        date=formatted_date,
                        updated_at=formatted_updated,
                        source="SJC",
                        source_url=url
                    ))
                except (ValueError, TypeError) as e:
                    logger.warning(f"[SBV] Error parsing gold price item: {e}")
                    continue
            
            logger.info(f"[SBV] Fetched {len(gold_prices)} gold prices from SJC")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[SBV] HTTP error fetching gold prices: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"[SBV] Request error fetching gold prices: {e}")
        except Exception as e:
            logger.error(f"[SBV] Error fetching gold prices: {e}")
        
        return gold_prices
    
    def _parse_gold_price_xml(self, xml_text: str, bank: str) -> List[Dict[str, Any]]:
        """
        Parse gold price data from XML response.
        
        XML format:
        <HashMap xmlns="">
            <goldPriceItems>
                <tenToChuc>...</tenToChuc>
                <khoiLuong>...</khoiLuong>
                ...
            </goldPriceItems>
            <status>success</status>
        </HashMap>
        """
        items = []
        
        try:
            soup = BeautifulSoup(xml_text, 'html.parser')
            
            # Check status
            status_elem = soup.find('status')
            if status_elem and status_elem.get_text(strip=True) != 'success':
                logger.warning(f"[SBV] Gold price XML returned non-success status for {bank}")
                return items
            
            # Find all goldPriceItems elements
            gold_items = soup.find_all('goldpriceitems')
            
            for item_elem in gold_items:
                item = {}
                
                # Extract all child elements
                for child in item_elem.children:
                    if hasattr(child, 'name') and child.name:
                        # Convert tag name to camelCase key
                        tag_name = child.name.lower()
                        # Map XML tags to expected JSON keys
                        key_map = {
                            'tentochuc': 'tenToChuc',
                            'khoiluong': 'khoiLuong',
                            'ngaydulieu': 'ngayDuLieu',
                            'loaivang': 'loaiVang',
                            'giamuaniemyet': 'giaMuaNiemYet',
                            'giabaniemyet': 'giaBanNiemYet',
                            'ngaycapnhat': 'ngayCapNhat',
                            'donvitinh': 'donViTinh'
                        }
                        key = key_map.get(tag_name, tag_name)
                        item[key] = child.get_text(strip=True)
                
                if item:
                    items.append(item)
            
            logger.debug(f"[SBV] Parsed {len(items)} items from XML for {bank}")
            
        except Exception as e:
            logger.error(f"[SBV] Error parsing gold price XML for {bank}: {e}")
        
        return items
        
        return gold_prices
    
    async def fetch_gold_prices(self, banks: Optional[List[str]] = None) -> List[GoldPriceData]:
        """
        Public method to fetch gold prices.
        
        Args:
            banks: List of bank codes to fetch. If None, fetch all configured banks.
                   Available: SJC, TPBank, BaoTinMinhChau
        
        Returns:
            List of GoldPriceData objects
        """
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            verify=settings.CRAWLERS_ENABLE_SSL
        ) as client:
            return await self._fetch_gold_prices(client, banks)
    
    async def _fetch_interest_rates(
        self, 
        client: httpx.AsyncClient
    ) -> tuple[List[PolicyRateData], List[InterbankRateData]]:
        """
        Fetch interest rates from SBV interest rate page.
        
        Returns:
            Tuple of (policy_rates, interbank_rates)
        """
        policy_rates = []
        interbank_rates = []
        
        try:
            await self._rate_limit()
            
            logger.info(f"[SBV] Fetching interest rates from {self.interest_rate_url}...")
            
            response = await client.get(self.interest_rate_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract policy rates (Bảng lãi suất)
            policy_rates = self._extract_policy_rates(soup)
            
            # Extract interbank rates (Lãi suất thị trường liên ngân hàng)
            interbank_rates = self._extract_interbank_rates(soup)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[SBV] HTTP error fetching interest rates: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"[SBV] Request error fetching interest rates: {e}")
        except Exception as e:
            logger.error(f"[SBV] Error fetching interest rates: {e}")
        
        return policy_rates, interbank_rates
    
    def _extract_policy_rates(self, soup: BeautifulSoup) -> List[PolicyRateData]:
        """
        Extract SBV policy rates from the interest rate page.
        
        Extracts:
        - Lãi suất tái chiết khấu (Rediscount rate)
        - Lãi suất tái cấp vốn (Refinancing rate)
        
        NOTE: Tại sao lãi suất liên ngân hàng có thể cao hơn nhiều so với lãi suất NHNN?
        ================================================================================
        Nếu lãi suất vay từ NHNN chỉ khoảng 4.5% - 5% (tái cấp vốn/OMO), việc vay nóng 
        ngân hàng bạn với lãi suất 9% nghe có vẻ phi lý. Tuy nhiên, thực tế điều này 
        vẫn xảy ra vì:
        
        1. Vấn đề "Tài sản đảm bảo" (Hết hàng để cầm cố):
           - Vay NHNN bắt buộc phải có Giấy tờ có giá (Trái phiếu Chính phủ) thế chấp
           - Nếu ngân hàng đã hết TPCP hoặc không nắm giữ đủ, họ không đủ điều kiện vay
           - Buộc phải vay tín chấp từ ngân hàng khác với lãi suất cao hơn
        
        2. Hạn mức (Room) tín dụng từ NHNN:
           - NHNN cấp hạn mức cho từng ngân hàng dựa trên quy mô và sức khỏe
           - Nếu đã full room từ kênh NHNN, buộc phải tìm đến thị trường liên ngân hàng
        
        3. Quy trình và Thủ tục (Tốc độ):
           - Liên ngân hàng: Cực nhanh, tiền về trong vài phút/trong ngày
           - Vay NHNN: Quy trình chặt chẽ, cần thời gian xử lý tài sản thế chấp
           - Khi "khát" thanh khoản cuối ngày, ngân hàng cần tiền ngay lập tức
        
        4. Yếu tố "Sợ mất uy tín" (Lender of Last Resort):
           - NHNN là "Người cho vay cuối cùng"
           - Liên tục tìm đến NHNN = tín hiệu ngân hàng đang yếu kém
           - Có thể bị giám sát đặc biệt hoặc hạ xếp hạng tín nhiệm
           - Thà vay lãi cao 9% bên ngoài để giữ "bộ mặt" sạch sẽ
        
        5. Sự khan hiếm cục bộ:
           - Khi nhiều ngân hàng cùng thiếu tiền (mùa cao điểm, rút tiền đầu cơ...)
           - Quy luật cung cầu đẩy lãi suất lên cao, bất chấp lãi suất điều hành thấp
        
        => Kết luận: Lãi suất liên ngân hàng cao hơn NHNN là bình thường, phản ánh 
           tình trạng thanh khoản thực tế của hệ thống ngân hàng.
        """
        policy_rates = []
        
        try:
            # Find the policy rate table (Bảng lãi suất)
            # Look for table with headers: Loại lãi suất, Giá trị, Văn bản quyết định, Ngày áp dụng
            tables = soup.find_all('table', class_='bi01-table')
            
            for table in tables:
                headers = table.find_all('th')
                header_texts = [h.get_text(strip=True) for h in headers]
                
                # Check if this is the policy rate table
                if 'Loại lãi suất' in header_texts and 'Văn bản quyết định' in header_texts:
                    rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            rate_type = cells[0].get_text(strip=True)
                            value_text = cells[1].get_text(strip=True)
                            decision = cells[2].get_text(strip=True)
                            effective_date = cells[3].get_text(strip=True)
                            
                            # Parse value (e.g., "3,000%" -> 3.0)
                            try:
                                value = float(value_text.replace('%', '').replace(',', '.').strip())
                            except ValueError:
                                logger.warning(f"[SBV] Could not parse policy rate value: {value_text}")
                                continue
                            
                            # Parse date
                            formatted_date = self._parse_date(effective_date)
                            
                            policy_rates.append(PolicyRateData(
                                rate_type=rate_type,
                                value=value,
                                decision=decision,
                                effective_date=formatted_date,
                                source_url=self.interest_rate_url
                            ))
                    
                    break  # Found the policy rate table
                    
        except Exception as e:
            logger.error(f"[SBV] Error extracting policy rates: {e}")
        
        return policy_rates
    
    def _extract_interbank_rates(self, soup: BeautifulSoup) -> List[InterbankRateData]:
        """
        Extract interbank market interest rates.
        
        Extracts rates for different terms:
        - Qua đêm (Overnight)
        - 1 Tuần, 2 Tuần
        - 1 Tháng, 3 Tháng, 6 Tháng, 9 Tháng
        """
        interbank_rates = []
        
        try:
            # Find the interbank rate section
            # Look for the subnote with "Ngày áp dụng"
            date_div = soup.find('div', class_='bi01-subnote')
            rate_date = ""
            
            if date_div:
                date_text = date_div.get_text(strip=True)
                # Extract date from "Ngày áp dụng: 02/02/2026"
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', date_text)
                if date_match:
                    rate_date = self._parse_date(date_match.group(1))
            
            # Find the interbank rate table
            tables = soup.find_all('table', class_='bi01-table')
            
            for table in tables:
                headers = table.find_all('th')
                header_texts = [h.get_text(strip=True) for h in headers]
                
                # Check if this is the interbank rate table
                if 'Thời hạn' in header_texts and 'Lãi suất BQ liên Ngân hàng' in ' '.join(header_texts):
                    rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            term_text = cells[0].get_text(strip=True)
                            
                            # Skip "Ghi chú" row
                            if 'Ghi chú' in term_text:
                                continue
                            
                            rate_text = cells[1].get_text(strip=True)
                            volume_text = cells[2].get_text(strip=True)
                            
                            # Check for note marker (*)
                            note = None
                            if '(*)' in rate_text or '(*)' in volume_text:
                                note = "Tham chiếu doanh số và lãi suất ngày trước"
                            
                            # Parse rate (e.g., "9,12" -> 9.12)
                            try:
                                rate_clean = re.sub(r'[^\d,.]', '', rate_text).replace(',', '.')
                                avg_rate = float(rate_clean) if rate_clean else 0.0
                            except ValueError:
                                avg_rate = 0.0
                            
                            # Parse volume (e.g., "902,773,0" -> 902773.0)
                            try:
                                # Remove (*) and other non-numeric chars except comma and dot
                                volume_clean = re.sub(r'[^\d,.]', '', volume_text)
                                # Handle Vietnamese number format (comma as thousand separator)
                                # "902,773,0" means 902773.0
                                parts = volume_clean.split(',')
                                if len(parts) > 1 and len(parts[-1]) == 1:
                                    # Last part is decimal
                                    volume = float(''.join(parts[:-1]) + '.' + parts[-1])
                                else:
                                    volume = float(volume_clean.replace(',', ''))
                            except ValueError:
                                volume = 0.0
                            
                            # Skip rows with no valid data
                            if avg_rate == 0.0 and volume == 0.0:
                                continue
                            
                            interbank_rates.append(InterbankRateData(
                                term=term_text,
                                avg_rate=avg_rate,
                                volume=volume,
                                date=rate_date,
                                note=note,
                                source_url=self.interest_rate_url
                            ))
                    
                    break  # Found the interbank rate table
                    
        except Exception as e:
            logger.error(f"[SBV] Error extracting interbank rates: {e}")
        
        return interbank_rates
    
    async def fetch_interest_rates(self) -> tuple[List[PolicyRateData], List[InterbankRateData]]:
        """
        Public method to fetch interest rates.
        
        Returns:
            Tuple of (policy_rates, interbank_rates)
        """
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            verify=settings.CRAWLERS_ENABLE_SSL
        ) as client:
            return await self._fetch_interest_rates(client)
    
    # ============================================================
    # CPI DATA EXTRACTION
    # ============================================================
    
    async def _fetch_cpi(
        self, 
        client: httpx.AsyncClient,
        max_items: int = 12
    ) -> List[CPIData]:
        """
        Fetch CPI (Consumer Price Index) data from SBV CPI page.
        
        CPI data is published monthly by General Statistics Office (Tổng cục Thống kê)
        and reported on SBV website.
        
        Args:
            client: httpx AsyncClient instance
            max_items: Maximum number of CPI items to fetch (default: 12 = last 12 months)
        
        Returns:
            List of CPIData objects
        """
        cpi_data = []
        
        try:
            await self._rate_limit()
            
            logger.info(f"[SBV] Fetching CPI data from {self.cpi_url}...")
            
            response = await client.get(self.cpi_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            cpi_data = self._extract_cpi_news(soup, max_items)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[SBV] HTTP error fetching CPI data: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"[SBV] Request error fetching CPI data: {e}")
        except Exception as e:
            logger.error(f"[SBV] Error fetching CPI data: {e}")
        
        return cpi_data
    
    def _extract_cpi_news(self, soup: BeautifulSoup, max_items: int = 12) -> List[CPIData]:
        """
        Extract CPI news items from the CPI page.
        
        Parses both featured news cards (news-card) and other news items (news-grid2).
        Extracts CPI values from titles like "CPI tháng 12/2025 tăng 0,19% so với tháng trước"
        """
        cpi_data = []
        seen_urls = set()
        
        try:
            # Pattern to extract month/year and MoM change from title
            # Examples:
            # - "CPI tháng 12/2025 tăng 0,19% so với tháng trước"
            # - "CPI tháng 3/2025 giảm 0,03% so với tháng trước"
            title_pattern = re.compile(
                r'CPI\s+tháng\s+(\d{1,2})/(\d{4})\s+(tăng|giảm)\s+([\d,]+)%',
                re.IGNORECASE
            )
            
            # Pattern to extract additional metrics from summary
            # - YoY: "tăng 3,38% so với cùng kỳ năm trước"
            # - YTD: "tăng 2,61% so với tháng 12/2024"
            # - Core inflation: "lạm phát cơ bản tăng 3,19%"
            yoy_pattern = re.compile(r'(tăng|giảm)\s+([\d,]+)%\s+so với cùng kỳ', re.IGNORECASE)
            ytd_pattern = re.compile(r'(tăng|giảm)\s+([\d,]+)%\s+so với tháng\s+12/', re.IGNORECASE)
            core_pattern = re.compile(r'lạm phát cơ bản\s+(tăng|giảm)\s+([\d,]+)%', re.IGNORECASE)
            
            # 1. Extract featured news cards (div.news-card)
            news_cards = soup.find_all('div', class_='news-card')
            
            for card in news_cards:
                if len(cpi_data) >= max_items:
                    break
                    
                # Get title and URL
                title_link = card.find('a', class_='news-title')
                if not title_link:
                    continue
                    
                title = title_link.get_text(strip=True)
                url = title_link.get('href', '')
                
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # Get summary
                summary_elem = card.find('span', class_='top-news-detail')
                summary = summary_elem.get_text(strip=True) if summary_elem else ""
                
                # Get publish date
                date_elem = card.find('div', class_='news-date')
                publish_date = ""
                if date_elem:
                    date_text = date_elem.get_text(strip=True).strip('()')
                    publish_date = self._parse_date(date_text)
                
                # Parse CPI data from title
                cpi_item = self._parse_cpi_from_title(
                    title, url, summary, publish_date,
                    title_pattern, yoy_pattern, ytd_pattern, core_pattern
                )
                
                if cpi_item:
                    cpi_data.append(cpi_item)
            
            # 2. Extract other news items from news-grid2
            news_grid2 = soup.find('div', class_='news-grid2')
            if news_grid2:
                other_links = news_grid2.find_all('a', class_='title-news-link')
                
                for link in other_links:
                    if len(cpi_data) >= max_items:
                        break
                        
                    url = link.get('href', '')
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    # Get title from h6
                    h6_elem = link.find('h6')
                    if not h6_elem:
                        continue
                    
                    # Extract title text (before the date span)
                    title = ""
                    for content in h6_elem.children:
                        if hasattr(content, 'name') and content.name == 'span':
                            break
                        if isinstance(content, str):
                            title += content
                        elif hasattr(content, 'get_text'):
                            title += content.get_text()
                    title = title.strip()
                    
                    # Get publish date
                    date_elem = link.find('span', class_='date-about')
                    publish_date = ""
                    if date_elem:
                        date_text = date_elem.get_text(strip=True).strip('()')
                        publish_date = self._parse_date(date_text)
                    
                    # Parse CPI data from title (no summary for these items)
                    cpi_item = self._parse_cpi_from_title(
                        title, url, "", publish_date,
                        title_pattern, yoy_pattern, ytd_pattern, core_pattern
                    )
                    
                    if cpi_item:
                        cpi_data.append(cpi_item)
                        
        except Exception as e:
            logger.error(f"[SBV] Error extracting CPI news: {e}")
        
        return cpi_data
    
    def _parse_cpi_from_title(
        self,
        title: str,
        url: str,
        summary: str,
        publish_date: str,
        title_pattern: re.Pattern,
        yoy_pattern: re.Pattern,
        ytd_pattern: re.Pattern,
        core_pattern: re.Pattern
    ) -> Optional[CPIData]:
        """Parse CPI data from title and summary text."""
        
        # Match title pattern
        title_match = title_pattern.search(title)
        if not title_match:
            return None
        
        month = int(title_match.group(1))
        year = int(title_match.group(2))
        direction = title_match.group(3).lower()
        value_str = title_match.group(4).replace(',', '.')
        
        try:
            mom_change = float(value_str)
            if direction == 'giảm':
                mom_change = -mom_change
        except ValueError:
            return None
        
        # Extract additional metrics from summary
        yoy_change = None
        ytd_change = None
        core_inflation = None
        
        text_to_search = summary or title
        
        # YoY change
        yoy_match = yoy_pattern.search(text_to_search)
        if yoy_match:
            try:
                yoy_val = float(yoy_match.group(2).replace(',', '.'))
                yoy_change = yoy_val if yoy_match.group(1).lower() == 'tăng' else -yoy_val
            except ValueError:
                pass
        
        # YTD change
        ytd_match = ytd_pattern.search(text_to_search)
        if ytd_match:
            try:
                ytd_val = float(ytd_match.group(2).replace(',', '.'))
                ytd_change = ytd_val if ytd_match.group(1).lower() == 'tăng' else -ytd_val
            except ValueError:
                pass
        
        # Core inflation
        core_match = core_pattern.search(text_to_search)
        if core_match:
            try:
                core_val = float(core_match.group(2).replace(',', '.'))
                core_inflation = core_val if core_match.group(1).lower() == 'tăng' else -core_val
            except ValueError:
                pass
        
        return CPIData(
            title=title,
            month=month,
            year=year,
            mom_change=mom_change,
            ytd_change=ytd_change,
            yoy_change=yoy_change,
            core_inflation=core_inflation,
            summary=summary if summary else None,
            publish_date=publish_date,
            source_url=url
        )
    
    async def fetch_cpi(self, max_items: int = 12) -> List[CPIData]:
        """
        Public method to fetch CPI data.
        
        Args:
            max_items: Maximum number of CPI items to fetch (default: 12)
        
        Returns:
            List of CPIData objects
        """
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            verify=settings.CRAWLERS_ENABLE_SSL
        ) as client:
            return await self._fetch_cpi(client, max_items)
    
    # ============================================================
    # OMO DATA EXTRACTION (Nghiệp vụ thị trường mở)
    # ============================================================
    
    async def _fetch_omo(
        self, 
        client: httpx.AsyncClient
    ) -> List[OMOData]:
        """
        Fetch Open Market Operations (OMO) data from SBV.
        
        OMO is the primary monetary policy tool used by SBV to manage liquidity 
        in the banking system. SBV conducts:
        - Repo (Mua kỳ hạn): Buy securities with agreement to sell back → inject liquidity
        - Reverse Repo (Bán kỳ hạn): Sell securities with agreement to buy back → withdraw liquidity
        
        Returns:
            List of OMOData objects with auction results
        """
        omo_data = []
        
        try:
            await self._rate_limit()
            
            logger.info(f"[SBV] Fetching OMO data from {self.omo_url}...")
            
            response = await client.get(self.omo_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            omo_data = self._extract_omo_results(soup)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[SBV] HTTP error fetching OMO data: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"[SBV] Request error fetching OMO data: {e}")
        except Exception as e:
            logger.error(f"[SBV] Error fetching OMO data: {e}")
        
        return omo_data
    
    def _extract_omo_results(self, soup: BeautifulSoup) -> List[OMOData]:
        """
        Extract OMO auction results from the page.
        
        Parses the table with columns:
        - Loại hình giao dịch (Transaction type)
        - Số thành viên tham gia/trúng thầu (Participants/Winners)
        - Khối lượng trúng thầu (Tỷ đồng) (Winning volume)
        - Lãi suất trúng thầu (%/năm) (Winning interest rate)
        """
        omo_data = []
        
        try:
            # Find the date from ls01-date div
            date_div = soup.find('div', class_='ls01-date')
            omo_date = ""
            
            if date_div:
                date_text = date_div.get_text(strip=True)
                # Parse "Ngày 03 tháng 02 năm 2026"
                date_match = re.search(
                    r'Ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
                    date_text
                )
                if date_match:
                    day = int(date_match.group(1))
                    month = int(date_match.group(2))
                    year = int(date_match.group(3))
                    omo_date = f"{year}-{month:02d}-{day:02d}"
            
            # Find the OMO results table (class="ls01-table")
            table = soup.find('table', class_='ls01-table')
            
            if not table:
                logger.warning("[SBV] Could not find OMO results table (ls01-table)")
                return omo_data
            
            tbody = table.find('tbody')
            if not tbody:
                logger.warning("[SBV] Could not find tbody in OMO table")
                return omo_data
            
            rows = tbody.find_all('tr')
            current_transaction_type = ""
            current_auction_round = 0  # Track auction round number
            auction_round_counters = {}  # Track rounds per transaction type
            
            for row in rows:
                row_class = row.get('class', [])
                
                # Check if this is a group header row (e.g., "Mua kỳ hạn")
                if 'ls01-group' in row_class:
                    td = row.find('td')
                    if td:
                        current_transaction_type = td.get_text(strip=True)
                        # Increment auction round for this transaction type
                        if current_transaction_type not in auction_round_counters:
                            auction_round_counters[current_transaction_type] = 0
                        auction_round_counters[current_transaction_type] += 1
                        current_auction_round = auction_round_counters[current_transaction_type]
                    continue
                
                # Check if this is a total row
                if 'ls01-total' in row_class:
                    # Extract total row data
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        # Total row format: [label, empty, volume, empty]
                        volume_text = cells[2].get_text(strip=True)
                        
                        try:
                            # Parse volume (e.g., "35.983,63" → 35983.63)
                            volume = self._parse_vietnamese_number(volume_text)
                            
                            omo_data.append(OMOData(
                                transaction_type=current_transaction_type,
                                auction_round=current_auction_round,
                                term="Tổng cộng",
                                participants="",
                                volume=volume,
                                interest_rate=0.0,
                                date=omo_date,
                                is_total=True,
                                source_url=self.omo_url
                            ))
                        except (ValueError, TypeError) as e:
                            logger.warning(f"[SBV] Could not parse OMO total row: {e}")
                    continue
                
                # Regular data row
                cells = row.find_all('td')
                if len(cells) >= 4:
                    try:
                        # Extract term (e.g., "- Kỳ hạn 7 ngày")
                        term_text = cells[0].get_text(strip=True)
                        # Clean up the term text
                        term = term_text.lstrip('-').strip()
                        if term.startswith('Kỳ hạn'):
                            term = term.replace('Kỳ hạn', '').strip()
                        
                        # Extract participants (e.g., "13/13")
                        participants = cells[1].get_text(strip=True)
                        
                        # Extract volume (e.g., "35.983,63")
                        volume_text = cells[2].get_text(strip=True)
                        volume = self._parse_vietnamese_number(volume_text)
                        
                        # Extract interest rate (e.g., "4,5")
                        rate_text = cells[3].get_text(strip=True)
                        interest_rate = self._parse_vietnamese_number(rate_text) if rate_text else 0.0
                        
                        omo_data.append(OMOData(
                            transaction_type=current_transaction_type,
                            auction_round=current_auction_round,
                            term=term,
                            participants=participants,
                            volume=volume,
                            interest_rate=interest_rate,
                            date=omo_date,
                            is_total=False,
                            source_url=self.omo_url
                        ))
                        
                    except (ValueError, TypeError, IndexError) as e:
                        logger.warning(f"[SBV] Could not parse OMO row: {e}")
                        continue
            
            logger.info(f"[SBV] Extracted {len(omo_data)} OMO results for {omo_date}")
            
        except Exception as e:
            logger.error(f"[SBV] Error extracting OMO results: {e}")
        
        return omo_data
    
    def _parse_vietnamese_number(self, text: str) -> float:
        """
        Parse Vietnamese number format to float.
        
        Vietnamese format uses:
        - Dot (.) as thousand separator
        - Comma (,) as decimal separator
        
        Examples:
        - "35.983,63" → 35983.63
        - "4,5" → 4.5
        - "15.000,00" → 15000.0
        """
        if not text:
            return 0.0
        
        # Remove thousand separators (dots) but keep decimal comma
        # First, replace comma with placeholder
        text = text.replace(',', '.')
        
        # If there are multiple dots, all but the last are thousand separators
        parts = text.split('.')
        if len(parts) > 2:
            # Join all but last part (integer part), then add decimal
            integer_part = ''.join(parts[:-1])
            decimal_part = parts[-1]
            text = f"{integer_part}.{decimal_part}"
        
        return float(text)
    
    async def fetch_omo(self) -> List[OMOData]:
        """
        Public method to fetch OMO (Open Market Operations) data.
        
        Returns:
            List of OMOData objects with auction results
        """
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            verify=settings.CRAWLERS_ENABLE_SSL
        ) as client:
            return await self._fetch_omo(client)

    def _extract_news(self, soup: BeautifulSoup) -> List[NewsItem]:
        """Extract news items from SBV homepage."""
        news_items = []
        
        try:
            news_links = soup.find_all('a', href=re.compile(r'/w/|/tin-tuc/|/su-kien/', re.I))
            seen_urls = set()
            
            for link in news_links:
                href = link.get('href', '')
                if not href or href in seen_urls:
                    continue
                    
                full_url = self._make_absolute_url(href)
                seen_urls.add(href)
                
                title = link.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                    
                # Try to find date nearby
                date_text = None
                parent = link.parent
                if parent:
                    date_elem = parent.find(['span', 'div'], class_=re.compile(r'date|ngay|time', re.I))
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        
                news_items.append(NewsItem(
                    title=title,
                    url=full_url,
                    date=date_text,
                    category="news"
                ))
                
                if len(news_items) >= 20:
                    break
                    
        except Exception as e:
            logger.error(f"[SBV] Error extracting news: {e}")
            
        return news_items
    
    def _extract_press_releases(self, soup: BeautifulSoup) -> List[NewsItem]:
        """Extract press releases (Thông cáo báo chí)."""
        press_releases = []
        
        try:
            press_links = soup.find_all('a', href=re.compile(r'/thong-cao|/tcbc/', re.I))
            seen_urls = set()
            
            for link in press_links:
                href = link.get('href', '')
                if not href or href in seen_urls:
                    continue
                    
                full_url = self._make_absolute_url(href)
                seen_urls.add(href)
                
                title = link.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                    
                press_releases.append(NewsItem(
                    title=title,
                    url=full_url,
                    category="press_release"
                ))
                
                if len(press_releases) >= 10:
                    break
                    
        except Exception as e:
            logger.error(f"[SBV] Error extracting press releases: {e}")
            
        return press_releases
    
    # ============================================================
    # ARTICLE CONTENT EXTRACTION
    # ============================================================
    
    async def fetch_article_content(
        self, 
        url: str, 
        extract_pdf: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch full content of a news article or press release.
        
        Args:
            url: Full URL to the article
            extract_pdf: Whether to download and extract text from PDF attachments
            
        Returns:
            Dict with title, content, date, attachments, pdf_content, etc.
        """
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient(
                timeout=60.0,
                follow_redirects=True,
                verify=settings.CRAWLERS_ENABLE_SSL
            ) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Initialize result
                result = {
                    "title": "",
                    "summary": "",
                    "content": "",
                    "date": "",
                    "url": url,
                    "categories": [],
                    "attachments": [],
                    "has_attachments": False,
                    "pdf_content": [],
                    "content_length": 0,
                    "total_content_length": 0
                }
                
                # Extract all article metadata and content
                result["title"] = self._extract_title(soup)
                result["date"] = self._extract_date(soup)
                result["categories"] = self._extract_categories(soup)
                result["summary"] = self._extract_summary(soup)
                result["attachments"], result["has_attachments"] = self._extract_attachments(soup)
                result["content"] = self._extract_article_content(soup, result["summary"])
                
                # Extract PDF content if requested
                if extract_pdf and result["has_attachments"] and PDF_SUPPORT:
                    result["pdf_content"] = await self._extract_all_pdfs(
                        result["attachments"], client
                    )
                
                # Calculate content lengths
                result["content_length"] = len(result["content"])
                result["total_content_length"] = result["content_length"] + sum(
                    len(pdf.get("text", "")) for pdf in result["pdf_content"]
                )
                
                # Return if meaningful content found OR has attachments (PDF docs contain main content)
                # Lower threshold since many SBV articles are short intros with PDF attachments
                has_meaningful_content = (
                    result["total_content_length"] > 20 or 
                    result["has_attachments"] or
                    result["title"]  # At minimum, we got the title
                )
                
                if has_meaningful_content:
                    logger.info(
                        f"[SBV] Extracted article: {result['title'][:50]}... "
                        f"(HTML: {result['content_length']}, PDFs: {len(result['pdf_content'])}, "
                        f"Attachments: {len(result['attachments'])}, Total: {result['total_content_length']} chars)"
                    )
                    return result
                else:
                    logger.warning(f"[SBV] No meaningful content found for {url}")
                    
        except Exception as e:
            logger.error(f"[SBV] Error fetching article {url}: {e}")
            
        return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title."""
        for selector in ['h1.title-page', 'h1.detail', 'h1']:
            elem = soup.find('h1', class_=selector.replace('h1.', '')) if '.' in selector else soup.find('h1')
            if elem:
                return elem.get_text(strip=True)
        return ""
    
    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract article date."""
        date_elem = soup.find('time', class_='author-time')
        if not date_elem:
            date_elem = soup.find('time', {'datetime': True})
        if not date_elem:
            date_elem = soup.find(['span', 'div'], class_=re.compile(r'date|ngay|time|publish', re.I))
        
        if date_elem:
            return self._parse_date(date_elem.get_text(strip=True))
        return ""
    
    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        """Extract article categories/tags."""
        categories = []
        tags_wrap = soup.find('ul', class_='tags-wrap')
        if tags_wrap:
            for tag_link in tags_wrap.find_all('a'):
                tag_text = tag_link.get_text(strip=True)
                if tag_text and tag_text not in categories:
                    categories.append(tag_text)
        return categories
    
    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """Extract article summary (sapo)."""
        # Try h4.singular-sapo first
        sapo_elem = soup.find('h4', class_='singular-sapo')
        if sapo_elem:
            text = sapo_elem.get_text(strip=True)
            if text:
                return text
        
        # If sapo is empty, try to get first paragraph from article-content
        article_content = soup.find('div', class_='article-content')
        if article_content:
            first_p = article_content.find('p')
            if first_p:
                text = first_p.get_text(strip=True)
                if text and len(text) > 20:
                    return text
        
        return ""
    
    def _extract_attachments(self, soup: BeautifulSoup) -> tuple[List[Dict], bool]:
        """Extract attachments from article."""
        attachments = []
        has_attachments = False
        
        # Check faq-send-upload div
        attachment_div = soup.find('div', class_='faq-send-upload')
        if attachment_div:
            has_attachments = True
            for link in attachment_div.find_all('a', href=True):
                if 'lnkAttachSOW' in link.get('id', ''):
                    continue
                    
                href = link.get('href', '')
                link_text = link.get_text(strip=True)
                
                if href and link_text:
                    attachments.append({
                        "name": link_text,
                        "url": self._make_absolute_url(href),
                        "type": self._get_file_type(href)
                    })
        
        # Check embedded PDFs
        for embed in soup.find_all('embed', {'type': 'application/pdf'}):
            src = embed.get('src', '')
            if src:
                full_url = self._make_absolute_url(src)
                if not any(att['url'] == full_url for att in attachments):
                    attachments.append({
                        "name": "Embedded PDF",
                        "url": full_url,
                        "type": "pdf"
                    })
                    has_attachments = True
        
        return attachments, has_attachments
    
    def _extract_article_content(self, soup: BeautifulSoup, summary: str) -> str:
        """Extract main article content."""
        content_elem = soup.find('div', class_='article-content')
        
        if content_elem:
            content_copy = BeautifulSoup(str(content_elem), 'html.parser')
            
            # Remove unwanted elements
            unwanted_selectors = [
                ('tag', ['script', 'style', 'nav', 'iframe']),
                ('class', ['audio_player_wrap', 'audio-player', 'hienthixemtruoc', 'noidungxemtruoc', 'faq-send-upload']),
                ('class_regex', r'social|share|cpanel'),
                ('id', ['lnkAttachSOW']),
            ]
            
            for sel_type, sel_value in unwanted_selectors:
                if sel_type == 'tag':
                    for elem in content_copy.find_all(sel_value):
                        elem.decompose()
                elif sel_type == 'class':
                    for cls in sel_value:
                        for elem in content_copy.find_all('div', class_=cls):
                            elem.decompose()
                elif sel_type == 'class_regex':
                    for elem in content_copy.find_all(['div', 'ul'], class_=re.compile(sel_value, re.I)):
                        elem.decompose()
                elif sel_type == 'id':
                    for id_val in sel_value:
                        for elem in content_copy.find_all(id=id_val):
                            elem.decompose()
            
            # Extract text content
            content_parts = []
            for elem in content_copy.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'li', 'div']):
                # Skip elements that contain other block elements (to avoid duplication)
                if elem.find_all(['p', 'h2', 'h3', 'h4', 'h5']):
                    continue
                    
                text = elem.get_text(strip=True)
                if not text or len(text) < 5:
                    continue
                
                # Skip if it's just "File đính kèm" or attachment labels
                if text in ['File đính kèm', 'Đính kèm'] or text.startswith('File đính kèm'):
                    continue
                    
                if 'img-caption' in str(elem.get('class', [])):
                    content_parts.append(f"[Ảnh: {text}]")
                    continue
                    
                if text != summary and text not in content_parts:
                    content_parts.append(text)
            
            content = "\n\n".join(content_parts)
            
            # Lower threshold to 30 chars (some articles have short intro + PDF attachments)
            if len(content) >= 30:
                return content
        
        # Fallback extraction
        return self._extract_content_fallback(soup)
    
    def _extract_content_fallback(self, soup: BeautifulSoup) -> str:
        """Fallback content extraction strategy."""
        
        def clean_content_div(div):
            """Remove unwanted elements from a content div."""
            # Remove unwanted tags
            for elem in div.find_all(['script', 'style', 'nav', 'iframe']):
                elem.decompose()
            # Remove audio player
            for elem in div.find_all('div', class_=re.compile(r'audio_player|audio-player', re.I)):
                elem.decompose()
            # Remove social/share elements
            for elem in div.find_all(['div', 'ul'], class_=re.compile(r'social|share|cpanel|singular-sidebar|singular-footer', re.I)):
                elem.decompose()
            # Remove attachment button (but keep attachment links)
            for elem in div.find_all('a', id='lnkAttachSOW'):
                elem.decompose()
            return div
        
        # Try print-content div
        print_content = soup.find('div', {'id': 'print-content'})
        if print_content:
            print_content = clean_content_div(BeautifulSoup(str(print_content), 'html.parser'))
            text = print_content.get_text(separator='\n', strip=True)
            # Clean up excessive whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)
        
        # Try journal-content-article
        journal_content = soup.find('div', class_='journal-content-article')
        if journal_content:
            journal_content = clean_content_div(BeautifulSoup(str(journal_content), 'html.parser'))
            text = journal_content.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)
            return journal_content.get_text(separator='\n', strip=True)
        
        # Last resort: find largest meaningful div
        all_divs = soup.find_all('div')
        div_sizes = [(div, len(div.get_text(strip=True))) for div in all_divs]
        div_sizes.sort(key=lambda x: x[1], reverse=True)
        
        for div, size in div_sizes:
            if 200 < size < 50000:
                classes = div.get('class', [])
                class_str = ' '.join(classes) if classes else ''
                if any(k in class_str.lower() for k in ['content', 'article', 'post', 'body', 'text']):
                    for elem in div.find_all(['script', 'style', 'nav']):
                        elem.decompose()
                    return div.get_text(separator='\n', strip=True)
        
        return ""
    
    # ============================================================
    # PDF EXTRACTION
    # ============================================================
    
    async def _extract_all_pdfs(
        self, 
        attachments: List[Dict], 
        client: httpx.AsyncClient
    ) -> List[Dict]:
        """Extract text from all PDF attachments."""
        pdf_content = []
        pdf_attachments = [att for att in attachments if att["type"] == "pdf"]
        
        for att in pdf_attachments:
            logger.info(f"[SBV] Extracting PDF: {att['name'][:50]}...")
            
            pdf_result = await self._download_and_extract_pdf(att["url"], client)
            
            if pdf_result and pdf_result.get("text"):
                pdf_content.append({
                    "name": att["name"],
                    "url": att["url"],
                    "text": pdf_result["text"],
                    "size_bytes": pdf_result.get("size_bytes", 0),
                })
                logger.info(f"[SBV] Extracted {len(pdf_result['text'])} chars from PDF")
        
        return pdf_content
    
    async def _download_and_extract_pdf(
        self, 
        url: str, 
        client: httpx.AsyncClient = None  # Not used anymore, kept for compatibility
    ) -> Optional[Dict[str, Any]]:
        """
        Download PDF and extract text content.
        
        Uses dedicated client with longer timeout (180s) for large PDFs.
        Implements retry logic with exponential backoff.
        Skips files larger than 5MB.
        """
        if not PDF_SUPPORT:
            logger.warning("[SBV] PDF extraction not available. Install pymupdf.")
            return None
        
        MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB limit for large Thong tu PDFs
        PDF_TIMEOUT = 900.0  # 15 minutes for large PDFs
        MAX_RETRIES = 3
        
        for attempt in range(MAX_RETRIES):
            try:
                await self._rate_limit()
                
                # Create dedicated client with longer timeout for PDF downloads
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=30.0,
                        read=PDF_TIMEOUT,
                        write=30.0,
                        pool=30.0
                    ),
                    follow_redirects=True,
                    verify=settings.CRAWLERS_ENABLE_SSL
                ) as pdf_client:
                    
                    # First, check file size with HEAD request
                    try:
                        head_response = await pdf_client.head(url, headers=self.headers)
                        content_length = head_response.headers.get('content-length')
                        if content_length and int(content_length) > MAX_PDF_SIZE:
                            logger.warning(f"[SBV] PDF too large ({int(content_length) / 1024 / 1024:.1f}MB > {MAX_PDF_SIZE / 1024 / 1024:.0f}MB), skipping: {url[:60]}...")
                            return None
                    except Exception:
                        # HEAD request failed, proceed with GET anyway
                        pass
                    
                    logger.info(f"[SBV] Downloading PDF (attempt {attempt + 1}/{MAX_RETRIES}): {url[:80]}...")
                    
                    response = await pdf_client.get(url, headers=self.headers)
                    response.raise_for_status()
                    
                    content_type = response.headers.get('content-type', '')
                    
                    # SBV returns 200 with HTML error page instead of 404
                    # Check if response is actually a PDF
                    if 'text/html' in content_type.lower():
                        # Check for SBV's "page not found" message
                        body_text = response.text[:500] if len(response.content) < 50000 else ""
                        if "không tồn tại" in body_text or "Địa chỉ độc giả truy nhập" in body_text:
                            logger.warning(f"[SBV] PDF page not found (SBV 404): {url[:60]}...")
                            return None
                        logger.warning(f"[SBV] URL returned HTML instead of PDF: {content_type}")
                        return None
                    
                    if 'pdf' not in content_type.lower() and not url.lower().endswith('.pdf'):
                        logger.warning(f"[SBV] URL does not appear to be a PDF: {content_type}")
                        return None
                    
                    pdf_bytes = response.content
                    
                    # Double check: PDF files start with %PDF
                    if not pdf_bytes.startswith(b'%PDF'):
                        logger.warning(f"[SBV] Response is not a valid PDF file: {url[:60]}...")
                        return None
                    
                    # Check actual size
                    if len(pdf_bytes) > MAX_PDF_SIZE:
                        logger.warning(f"[SBV] PDF too large ({len(pdf_bytes) / 1024 / 1024:.1f}MB > {MAX_PDF_SIZE / 1024 / 1024:.0f}MB), skipping: {url[:60]}...")
                        return None
                    
                    text_content = self._extract_text_from_pdf_bytes(pdf_bytes)
                    
                    if text_content:
                        return {
                            "text": text_content,
                            "source_url": url,
                            "size_bytes": len(pdf_bytes),
                        }
                    
                    return None
            
            except asyncio.CancelledError:
                logger.warning(f"[SBV] PDF download cancelled: {url[:60]}...")
                return None  # Don't retry on cancellation
                    
            except httpx.TimeoutException as e:
                logger.warning(f"[SBV] Timeout downloading PDF (attempt {attempt + 1}/{MAX_RETRIES}): {url[:60]}...")
                if attempt < MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 5  # 5s, 10s, 15s backoff
                    logger.info(f"[SBV] Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[SBV] Failed to download PDF after {MAX_RETRIES} attempts: {url[:60]}...")
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"[SBV] HTTP error downloading PDF {url}: {e.response.status_code}")
                return None  # Don't retry on HTTP errors
                
            except httpx.RequestError as e:
                logger.warning(f"[SBV] Request error downloading PDF (attempt {attempt + 1}): {url[:60]}... - {e}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 3
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"[SBV] Error extracting PDF {url}: {e}")
                return None
        
        return None
    
    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes using PyMuPDF."""
        if not PDF_SUPPORT:
            return ""
        
        doc = None
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            text_parts = []
            num_pages = len(doc)
            
            for page_num in range(num_pages):
                page = doc[page_num]
                text = page.get_text("text")
                
                if text.strip():
                    text_parts.append(f"--- Trang {page_num + 1} ---\n{text.strip()}")
            
            full_text = "\n\n".join(text_parts)
            full_text = self._clean_pdf_text(full_text)
            
            logger.info(f"[SBV] Extracted {len(full_text)} chars from PDF ({num_pages} pages)")
            return full_text
            
        except Exception as e:
            logger.error(f"[SBV] Error parsing PDF: {e}")
            return ""
        finally:
            if doc:
                doc.close()
    
    def _clean_pdf_text(self, text: str) -> str:
        """Clean up extracted PDF text."""
        if not text:
            return ""
        
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            if not cleaned_lines and not line:
                continue
            
            # Skip common page number patterns
            if re.match(r'^Trang \d+/\d+$', line) or re.match(r'^\d+/\d+$', line):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    # ============================================================
    # UTILITY METHODS
    # ============================================================
    
    def _parse_date(self, date_text: str) -> str:
        """Parse and normalize date from various formats."""
        if not date_text:
            return ""
        
        date_formats = [
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y",
            "%Y-%m-%d",
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_text.strip(), fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S") if ":" in date_text else dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return date_text.strip()
    
    def _get_file_type(self, url: str) -> str:
        """Determine file type from URL."""
        url_lower = url.lower()
        
        if '.pdf' in url_lower:
            return "pdf"
        elif '.doc' in url_lower or '.docx' in url_lower:
            return "word"
        elif '.xls' in url_lower or '.xlsx' in url_lower:
            return "excel"
        elif '.zip' in url_lower or '.rar' in url_lower:
            return "archive"
        elif any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif']):
            return "image"
        else:
            return "other"
    
    async def fetch_exchange_rate_history(self, days: int = 30) -> List[ExchangeRateData]:
        """Get historical exchange rate data from homepage."""
        rates = []
        
        try:
            await self._rate_limit()
            
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                verify=settings.CRAWLERS_ENABLE_SSL
            ) as client:
                response = await client.get(self.base_url, headers=self.headers)
                response.raise_for_status()
                html_content = response.text
                
                rate_match = re.search(r'var\s+tyGiaValues\s*=\s*\[([\d,\s]+)\]', html_content)
                date_match = re.search(r'var\s+dates\s*=\s*\[(.*?)\]', html_content, re.DOTALL)
                
                if rate_match and date_match:
                    rate_values = [float(r.strip()) for r in rate_match.group(1).split(',') if r.strip()]
                    date_values = re.findall(r'"([^"]+)"', date_match.group(1))
                    
                    for rate, date in list(zip(rate_values, date_values))[-days:]:
                        try:
                            dt = datetime.strptime(date, "%d-%m-%Y")
                            formatted_date = dt.strftime("%Y-%m-%d")
                        except:
                            formatted_date = date
                            
                        rates.append(ExchangeRateData(
                            date=formatted_date,
                            central_rate=rate,
                            source_url=self.base_url
                        ))
                        
        except Exception as e:
            logger.error(f"[SBV] Error fetching exchange rate history: {e}")
            
        return rates
    
    # ============================================================
    # MAIN RUN METHOD 
    # ============================================================
    
    async def run(
        self, 
        max_articles: Optional[int] = None,
        extract_pdf: bool = True,
        news_only: bool = False,
        save_raw: bool = False,
        existing_titles: Optional[set] = None,
    ) -> CrawlResult:
        """
        Run full crawl with content extraction and save to file.
        
        Overrides BaseCrawler.run() to include full article content.
        
        This method:
        1. Fetch homepage data (exchange rates, credit data, news list)
        2. Filter out articles already in database (by title)
        3. Fetch full content for new articles only
        4. Extract PDF attachments if available
        5. Save results to file
        
        Args:
            max_articles: Maximum articles to fetch full content. If None, fetch all articles.
            extract_pdf: Whether to extract PDF text (default: True)
            news_only: If True, only fetch news content, skip exchange rates etc.
            existing_titles: Set of titles already in DB (skip fetching content for these)
            
        Returns:
            CrawlResult with all data
        """
        logger.info(f"[{self.name}] Starting full crawl run (max_articles={max_articles}, extract_pdf={extract_pdf})...")
        
        all_data = []
        errors = []
        stats = {
            "articles_fetched": 0,
            "articles_failed": 0,
            "total_html_chars": 0,
            "total_pdf_files": 0,
            "total_pdf_chars": 0
        }
        
        # Initialize counters for metadata
        skipped_count = 0
        exchange_rates = []
        credit_data = []
        gold_prices = []
        policy_rates = []
        interbank_rates = []
        cpi_data = []
        omo_data = []
        
        try:
            # Step 1: Fetch homepage data
            logger.info(f"[{self.name}] Step 1: Fetching homepage data...")
            homepage_result = await self.fetch()
            
            if not homepage_result.success:
                return homepage_result
            
            # Separate data types
            exchange_rates = [x for x in homepage_result.data if x.get('type') == 'exchange_rate']
            credit_data = [x for x in homepage_result.data if x.get('type') == 'credit']
            gold_prices = [x for x in homepage_result.data if x.get('type') == 'gold_price']
            policy_rates = [x for x in homepage_result.data if x.get('type') == 'policy_rate']
            interbank_rates = [x for x in homepage_result.data if x.get('type') == 'interbank_rate']
            cpi_data = [x for x in homepage_result.data if x.get('type') == 'cpi']
            omo_data = [x for x in homepage_result.data if x.get('type') == 'omo']
            news_items = [
                x for x in homepage_result.data 
                if x.get('type') in ['news', 'press_release']
            ]
            
            # Add non-news data if not news_only mode
            if not news_only:
                all_data.extend(exchange_rates)
                all_data.extend(credit_data)
                all_data.extend(gold_prices)
                all_data.extend(policy_rates)
                all_data.extend(interbank_rates)
                all_data.extend(cpi_data)
                all_data.extend(omo_data)
                logger.info(
                    f"[{self.name}] Added {len(exchange_rates)} exchange rates, "
                    f"{len(credit_data)} credit data, {len(gold_prices)} gold prices, "
                    f"{len(policy_rates)} policy rates, {len(interbank_rates)} interbank rates, "
                    f"{len(cpi_data)} CPI data, {len(omo_data)} OMO data"
                )
            
            # Step 2: Filter out articles already in database
            existing_titles = existing_titles or set()
            new_news_items = []
            skipped_count = 0
            
            for item in news_items:
                title = (item.get("title") or "").strip()
                if title and title in existing_titles:
                    skipped_count += 1
                    logger.debug(f"[{self.name}] Skipping duplicate: {title[:50]}...")
                    continue
                new_news_items.append(item)
            
            if skipped_count > 0:
                logger.info(f"[{self.name}] Skipped {skipped_count} existing articles, {len(new_news_items)} new to fetch")
            
            # Step 3: Fetch full content for new articles only
            articles_to_fetch = new_news_items if max_articles is None else new_news_items[:max_articles]
            logger.info(f"[{self.name}] Step 3: Fetching full content for {len(articles_to_fetch)} articles...")
            
            for i, news_item in enumerate(articles_to_fetch, 1):
                url = news_item.get('source_url', '')
                title = news_item.get('title', 'N/A')
                
                logger.info(f"[{self.name}] [{i}/{len(articles_to_fetch)}] Fetching: {title[:50]}...")
                
                try:
                    # Fetch full article content
                    article_content = await self.fetch_article_content(url, extract_pdf=extract_pdf)
                    
                    if article_content:
                        # Create enriched news item with full content
                        enriched_item = {
                            **news_item,
                            "content": article_content.get("content", ""),
                            "full_title": article_content.get("title", news_item.get("title", "")),
                            "summary": article_content.get("summary", ""),
                            "date": article_content.get("date", news_item.get("date", "")),
                            "categories": article_content.get("categories", []),
                            "attachments": article_content.get("attachments", []),
                            "has_attachments": article_content.get("has_attachments", False),
                            "pdf_content": article_content.get("pdf_content", []),
                            "content_length": article_content.get("content_length", 0),
                            "total_content_length": article_content.get("total_content_length", 0),
                            "fetch_success": True
                        }
                        
                        all_data.append(enriched_item)
                        stats["articles_fetched"] += 1
                        stats["total_html_chars"] += article_content.get("content_length", 0)
                        stats["total_pdf_files"] += len(article_content.get("pdf_content", []))
                        stats["total_pdf_chars"] += sum(
                            len(pdf.get("text", "")) for pdf in article_content.get("pdf_content", [])
                        )
                    else:
                        # Failed to fetch content, add with error flag
                        all_data.append({
                            **news_item,
                            "content": "",
                            "fetch_success": False,
                            "fetch_error": "Failed to extract content"
                        })
                        stats["articles_failed"] += 1
                        
                except Exception as e:
                    logger.error(f"[{self.name}] Error fetching article {url}: {e}")
                    all_data.append({
                        **news_item,
                        "content": "",
                        "fetch_success": False,
                        "fetch_error": str(e)
                    })
                    stats["articles_failed"] += 1
                    errors.append(f"Article fetch error: {str(e)}")
            
            # NOTE: We only return articles that were actually fetched.
            # Articles beyond max_articles or with existing titles are NOT included.
            
            # Log summary
            logger.info(
                f"[{self.name}] Fetch complete: {stats['articles_fetched']} articles, "
                f"{stats['total_html_chars']:,} HTML chars, "
                f"{stats['total_pdf_files']} PDFs ({stats['total_pdf_chars']:,} chars)"
            )
            
        except Exception as e:
            error_msg = f"Unexpected error in run: {str(e)}"
            logger.exception(f"[{self.name}] {error_msg}")
            errors.append(error_msg)
        
        # Create result with stats metadata
        result = CrawlResult(
            source=self.name,
            crawled_at=datetime.now(),
            success=len(all_data) > 0,
            data=all_data,
            error="; ".join(errors) if errors else None
        )
        
        # Add stats to result - store stats in first item as metadata
        if all_data:
            metadata_item = {
                "type": "metadata",
                "category": "crawl_stats",
                "name": "SBV Crawl Statistics",
                "stats": stats,
                "total_items": len(all_data),
                "exchange_rates_count": len(exchange_rates) if not news_only else 0,
                "credit_data_count": len(credit_data) if not news_only else 0,
                "gold_prices_count": len(gold_prices) if not news_only else 0,
                "policy_rates_count": len(policy_rates) if not news_only else 0,
                "interbank_rates_count": len(interbank_rates) if not news_only else 0,
                "cpi_data_count": len(cpi_data) if not news_only else 0,
                "omo_data_count": len(omo_data) if not news_only else 0,
                "news_with_content": stats["articles_fetched"],
                "news_failed": stats["articles_failed"],
                "news_skipped_existing": skipped_count,
            }
            all_data.insert(0, metadata_item)
        
        # Save results to file
        if result.success:
            logger.info(f"[{self.name}] Successfully crawled {len(result.data)} items")
            
            # Save raw data if requested (for debugging)
            if save_raw:
                self.save_raw(result)
            
            # Transform and save transformed output
            output = self.transformer.transform(result.to_dict())
            self.save_transformed(output)
            logger.info(f"[{self.name}] Transformed: {output.summary()}")
        else:
            logger.error(f"[{self.name}] Crawl failed: {result.error}")
        
        return result

# ============================================================
# DATA SOURCES SUMMARY
# ============================================================
"""
SBV Crawler Data Sources:

✅ IMPLEMENTED:
1. Exchange Rate (Tỷ giá trung tâm USD/VND)
   - Source: Homepage JavaScript variables
   
2. Credit Data (Dư nợ tín dụng)
   - Source: Homepage JavaScript charts
   
3. Gold Prices (Giá vàng)
   - Source: https://www.sbv.gov.vn/o/goldprice/v1.0/gold-price?bank={bank}
   - Banks: SJC, TPBank, BaoTinMinhChau
   - Supports both JSON and XML responses
   
4. Interest Rates (Lãi suất):
   - Policy rates (Lãi suất NHNN): Tái chiết khấu, Tái cấp vốn
   - Interbank rates (Lãi suất liên ngân hàng): Qua đêm to 9 tháng
   - Source: https://www.sbv.gov.vn/vi/lãi-suất1
   
5. CPI Data (Chỉ số giá tiêu dùng)
   - Source: https://www.sbv.gov.vn/vi/cpi
   - Monthly CPI news with MoM, YoY, YTD changes
   
6. OMO Operations (Nghiệp vụ thị trường mở)
   - Source: https://sbv.gov.vn/vi/nghiệp-vụ-thị-trường-mở
   - Auction results: Volume, interest rate, participants
   
7. News & Press Releases
   - Source: Homepage news sections
   - Full article content with PDF extraction

📋 POTENTIAL ADDITIONS:
- Balance of Payments (Cán cân thanh toán quốc tế)
- Money Supply (M2, M0)
- Required Reserve Ratio
- Legal Documents (Văn bản QPPL)
"""