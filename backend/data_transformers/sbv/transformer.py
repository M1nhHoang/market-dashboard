"""
SBV Data Transformer

Transforms raw SBV crawler output into unified CrawlerOutput structure.

Raw SBV output format:
{
    "source": "sbv",
    "crawled_at": "2026-02-04T11:40:24.018560",
    "success": true,
    "data": [
        {"type": "metadata", ...},
        {"type": "exchange_rate", ...},
        {"type": "gold_price", ...},
        {"type": "policy_rate", ...},
        {"type": "interbank_rate", ...},
        {"type": "cpi", ...},
        {"type": "omo", ...},
        {"type": "news", ...}
    ]
}
"""

import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from collections import defaultdict

from data_transformers.base import BaseTransformer
from data_transformers.models import (
    CrawlerOutput,
    MetricRecord,
    EventRecord,
    MetricType,
    EventType,
)
from .mappings import (
    INTERBANK_TERM_MAP,
    POLICY_RATE_MAP,
    GOLD_PRICE_MAP,
)


logger = logging.getLogger(__name__)


class SBVTransformer(BaseTransformer):
    """
    Transforms SBV crawler output to unified CrawlerOutput.
    
    Handles these raw types:
    - exchange_rate → MetricRecord (exchange_rate)
    - interbank_rate → MetricRecord (interbank_rate)
    - policy_rate → MetricRecord (policy_rate)
    - gold_price → MetricRecord (gold_price)
    - cpi → MetricRecord (cpi)
    - omo → MetricRecord (omo) - aggregated
    - news → EventRecord (news/press_release)
    """
    
    @property
    def source_name(self) -> str:
        return "sbv"
    
    def transform(self, raw_data: Dict[str, Any]) -> CrawlerOutput:
        """
        Transform raw SBV crawler data to CrawlerOutput.
        
        Args:
            raw_data: Full raw response from SBV crawler with structure:
                      {"source": "sbv", "crawled_at": "...", "success": true, "data": [...]}
        
        Returns:
            CrawlerOutput with metrics and events populated
        """
        # Parse crawled_at
        crawled_at = self._parse_datetime(raw_data.get("crawled_at"))
        
        # Get data array
        data_items = raw_data.get("data", [])
        if not self.validate_raw_data(data_items):
            return CrawlerOutput(
                source=self.source_name,
                crawled_at=crawled_at,
                success=False,
                error="Empty or invalid data array",
            )
        
        # Initialize collectors
        metrics: List[MetricRecord] = []
        events: List[EventRecord] = []
        stats = defaultdict(int)
        errors = []
        
        # Track OMO data for aggregation
        omo_by_date: Dict[str, Dict[str, Any]] = {}
        
        # Process each item
        for item in data_items:
            item_type = item.get("type")
            
            try:
                if item_type == "metadata":
                    # Extract crawl stats
                    stats.update(item.get("stats", {}))
                    stats["total_items"] = item.get("total_items", 0)
                    
                elif item_type == "exchange_rate":
                    metric = self._transform_exchange_rate(item)
                    if metric:
                        metrics.append(metric)
                        stats["exchange_rate_count"] += 1
                        
                elif item_type == "interbank_rate":
                    metric = self._transform_interbank_rate(item)
                    if metric:
                        metrics.append(metric)
                        stats["interbank_rate_count"] += 1
                        
                elif item_type == "policy_rate":
                    metric = self._transform_policy_rate(item)
                    if metric:
                        metrics.append(metric)
                        stats["policy_rate_count"] += 1
                        
                elif item_type == "gold_price":
                    metric = self._transform_gold_price(item)
                    if metric:
                        metrics.append(metric)
                        stats["gold_price_count"] += 1
                        
                elif item_type == "cpi":
                    cpi_metrics = self._transform_cpi(item)
                    metrics.extend(cpi_metrics)
                    stats["cpi_count"] += 1
                    
                elif item_type == "omo":
                    # Collect OMO data for aggregation
                    self._collect_omo_data(item, omo_by_date)
                    stats["omo_raw_count"] += 1
                    
                elif item_type == "news":
                    event = self._transform_news(item)
                    if event:
                        events.append(event)
                        stats["news_count"] += 1
                        
            except Exception as e:
                logger.error(f"Error transforming item type={item_type}: {e}")
                errors.append(f"{item_type}: {str(e)}")
        
        # Aggregate OMO data and create metrics
        omo_metrics = self._aggregate_omo(omo_by_date)
        metrics.extend(omo_metrics)
        stats["omo_aggregated_count"] = len(omo_metrics)
        
        # Add errors to stats
        stats["errors"] = errors
        
        return CrawlerOutput(
            source=self.source_name,
            crawled_at=crawled_at,
            success=raw_data.get("success", True),
            stats=dict(stats),
            metrics=metrics,
            events=events,
            calendar=[],  # SBV doesn't provide calendar data
        )
    
    # ========================================
    # METRIC TRANSFORMERS
    # ========================================
    
    def _transform_exchange_rate(self, item: Dict[str, Any]) -> Optional[MetricRecord]:
        """Transform exchange rate item to MetricRecord."""
        value = item.get("value")
        if value is None:
            return None
            
        return MetricRecord(
            metric_type=MetricType.EXCHANGE_RATE,
            metric_id="usd_vnd_central",
            value=float(value),
            unit=item.get("unit", "VND"),
            date=self._parse_date(item.get("date")),
            name="USD/VND Central Rate",
            name_vi="Tỷ giá trung tâm USD/VND",
            source=item.get("source", "SBV"),
            source_url=item.get("source_url"),
        )
    
    def _transform_interbank_rate(self, item: Dict[str, Any]) -> Optional[MetricRecord]:
        """Transform interbank rate item to MetricRecord."""
        term = item.get("term")
        if not term:
            return None
            
        # Map term to indicator ID
        indicator_id = INTERBANK_TERM_MAP.get(term)
        if not indicator_id:
            logger.warning(f"Unknown interbank term: {term}")
            return None
            
        avg_rate = item.get("avg_rate")
        if avg_rate is None:
            return None
            
        return MetricRecord(
            metric_type=MetricType.INTERBANK_RATE,
            metric_id=indicator_id,
            value=float(avg_rate),
            unit=item.get("unit_rate", "% năm"),
            date=self._parse_date(item.get("date")),
            name=f"Interbank {term}",
            name_vi=f"Lãi suất liên ngân hàng {term}",
            attributes={
                "term": term,
                "volume": item.get("volume"),
                "volume_unit": item.get("unit_volume", "Tỷ đồng"),
                "note": item.get("note"),
            },
            source=item.get("source", "SBV"),
            source_url=item.get("source_url"),
        )
    
    def _transform_policy_rate(self, item: Dict[str, Any]) -> Optional[MetricRecord]:
        """Transform policy rate item to MetricRecord."""
        rate_type = item.get("rate_type", "")
        value = item.get("value")
        
        if value is None:
            return None
        
        # Find matching rate type
        indicator_id = None
        name = None
        name_vi = None
        
        for key, mapping in POLICY_RATE_MAP.items():
            if key.lower() in rate_type.lower():
                indicator_id = mapping["indicator_id"]
                name = mapping["name"]
                name_vi = mapping["name_vi"]
                break
        
        if not indicator_id:
            logger.warning(f"Unknown policy rate type: {rate_type}")
            return None
            
        return MetricRecord(
            metric_type=MetricType.POLICY_RATE,
            metric_id=indicator_id,
            value=float(value),
            unit=item.get("unit", "%"),
            date=self._parse_date(item.get("effective_date")),
            name=name,
            name_vi=name_vi,
            attributes={
                "decision": item.get("decision"),
                "effective_date": item.get("effective_date"),
            },
            source=item.get("source", "SBV"),
            source_url=item.get("source_url"),
        )
    
    def _transform_gold_price(self, item: Dict[str, Any]) -> Optional[MetricRecord]:
        """Transform gold price item to MetricRecord."""
        gold_type = item.get("gold_type", "")
        buy_price = item.get("buy_price")
        organization = item.get("organization", "")
        
        if buy_price is None or buy_price == 0:
            return None
        
        # Only track main SJC price from the official SJC company
        mapping = GOLD_PRICE_MAP.get("SJC")
        if not mapping:
            return None
            
        # Only accept if from official SJC and is the main price type
        is_official_sjc = "SJC" in organization.upper() and "VÀNG BẠC ĐÁ QUÝ SÀI GÒN" in organization
        is_main_type = gold_type == "SJC"
        
        if not (is_official_sjc and is_main_type):
            return None
        
        return MetricRecord(
            metric_type=MetricType.GOLD_PRICE,
            metric_id=mapping["indicator_id"],
            value=float(buy_price),
            unit="VND/lượng",
            date=self._parse_date(item.get("date")),
            name=mapping["name"],
            name_vi=mapping["name_vi"],
            attributes={
                "buy_price": item.get("buy_price"),
                "sell_price": item.get("sell_price"),
                "organization": organization,
                "gold_type": gold_type,
                "original_unit": item.get("price_unit"),
            },
            source=item.get("source", "SBV"),
            source_url=item.get("source_url"),
        )
    
    def _transform_cpi(self, item: Dict[str, Any]) -> List[MetricRecord]:
        """
        Transform CPI item to multiple MetricRecords.
        
        One CPI item can produce multiple metrics:
        - cpi_mom: Month-over-month change
        - cpi_yoy: Year-over-year change
        - cpi_ytd: Year-to-date change
        - core_inflation: Core inflation
        """
        metrics = []
        
        month = item.get("month")
        year = item.get("year")
        date_value = self._parse_date(item.get("date"))
        period = f"{year}-{month:02d}" if month and year else None
        
        base_attrs = {
            "month": month,
            "year": year,
            "title": item.get("title"),
            "summary": item.get("summary"),
        }
        
        # MoM change
        mom_change = item.get("mom_change") or item.get("value")
        if mom_change is not None:
            metrics.append(MetricRecord(
                metric_type=MetricType.CPI,
                metric_id="cpi_mom",
                value=float(mom_change),
                unit="%",
                date=date_value,
                period=period,
                name="CPI Month-over-Month",
                name_vi="CPI so với tháng trước",
                attributes=base_attrs,
                source=item.get("source", "SBV/GSO"),
                source_url=item.get("source_url"),
            ))
        
        # YoY change
        yoy_change = item.get("yoy_change")
        if yoy_change is not None:
            metrics.append(MetricRecord(
                metric_type=MetricType.CPI,
                metric_id="cpi_yoy",
                value=float(yoy_change),
                unit="%",
                date=date_value,
                period=period,
                name="CPI Year-over-Year",
                name_vi="CPI so với cùng kỳ năm trước",
                attributes=base_attrs,
                source=item.get("source", "SBV/GSO"),
                source_url=item.get("source_url"),
            ))
        
        # YTD change
        ytd_change = item.get("ytd_change")
        if ytd_change is not None:
            metrics.append(MetricRecord(
                metric_type=MetricType.CPI,
                metric_id="cpi_ytd",
                value=float(ytd_change),
                unit="%",
                date=date_value,
                period=period,
                name="CPI Year-to-Date",
                name_vi="CPI bình quân từ đầu năm",
                attributes=base_attrs,
                source=item.get("source", "SBV/GSO"),
                source_url=item.get("source_url"),
            ))
        
        # Core inflation
        core_inflation = item.get("core_inflation")
        if core_inflation is not None:
            metrics.append(MetricRecord(
                metric_type=MetricType.CPI,
                metric_id="core_inflation",
                value=float(core_inflation),
                unit="%",
                date=date_value,
                period=period,
                name="Core Inflation",
                name_vi="Lạm phát cơ bản",
                attributes=base_attrs,
                source=item.get("source", "SBV/GSO"),
                source_url=item.get("source_url"),
            ))
        
        return metrics
    
    def _collect_omo_data(self, item: Dict[str, Any], omo_by_date: Dict[str, Dict[str, Any]]):
        """
        Collect OMO data for later aggregation.
        
        OMO data comes in multiple records per day, we need to aggregate:
        - Total inject (sum of all "Mua kỳ hạn" totals)
        - Total withdraw (sum of all "Bán kỳ hạn" totals)
        - Net = inject - withdraw
        - Breakdown by term
        """
        date_str = item.get("date")
        if not date_str:
            return
            
        if date_str not in omo_by_date:
            omo_by_date[date_str] = {
                "inject_total": 0.0,
                "withdraw_total": 0.0,
                "by_term": defaultdict(float),
                "source": item.get("source", "SBV"),
                "source_url": item.get("source_url"),
            }
        
        # Only process "Tổng cộng" (total) records for totals
        if not item.get("is_total"):
            # But collect term breakdown from non-total records
            term = item.get("term")
            volume = item.get("volume", 0) or 0
            if term and term != "Tổng cộng":
                term_key = self._normalize_omo_term(term)
                trans_type = item.get("transaction_type", "")
                
                if "Mua" in trans_type:  # Inject
                    omo_by_date[date_str]["by_term"][term_key] += float(volume)
            return
        
        # Process total records
        trans_type = item.get("transaction_type", "")
        volume = item.get("volume", 0) or 0
        
        if "Mua" in trans_type:  # Mua kỳ hạn = Inject (reverse repo)
            omo_by_date[date_str]["inject_total"] += float(volume)
        elif "Bán" in trans_type:  # Bán kỳ hạn = Withdraw (repo)
            omo_by_date[date_str]["withdraw_total"] += float(volume)
    
    def _aggregate_omo(self, omo_by_date: Dict[str, Dict[str, Any]]) -> List[MetricRecord]:
        """Aggregate collected OMO data into metrics."""
        metrics = []
        
        for date_str, data in omo_by_date.items():
            date_value = self._parse_date(date_str)
            inject = data["inject_total"]
            withdraw = data["withdraw_total"]
            net = inject - withdraw
            
            # Common attributes
            attrs = {
                "inject": inject,
                "withdraw": withdraw,
                "by_term": dict(data["by_term"]),
            }
            
            # Create net OMO metric (main indicator)
            metrics.append(MetricRecord(
                metric_type=MetricType.OMO,
                metric_id="omo_net_daily",
                value=net,
                unit="Tỷ đồng",
                date=date_value,
                name="OMO Net Daily",
                name_vi="OMO ròng trong ngày",
                attributes=attrs,
                source=data.get("source", "SBV"),
                source_url=data.get("source_url"),
            ))
            
            # Optionally create inject/withdraw metrics
            if inject > 0:
                metrics.append(MetricRecord(
                    metric_type=MetricType.OMO,
                    metric_id="omo_inject_daily",
                    value=inject,
                    unit="Tỷ đồng",
                    date=date_value,
                    name="OMO Daily Injection",
                    name_vi="OMO bơm trong ngày",
                    attributes=attrs,
                    source=data.get("source", "SBV"),
                    source_url=data.get("source_url"),
                ))
            
            if withdraw > 0:
                metrics.append(MetricRecord(
                    metric_type=MetricType.OMO,
                    metric_id="omo_withdraw_daily",
                    value=withdraw,
                    unit="Tỷ đồng",
                    date=date_value,
                    name="OMO Daily Withdrawal",
                    name_vi="OMO hút trong ngày",
                    attributes=attrs,
                    source=data.get("source", "SBV"),
                    source_url=data.get("source_url"),
                ))
        
        return metrics
    
    def _normalize_omo_term(self, term: str) -> str:
        """Normalize OMO term to standard format."""
        term = term.strip()
        
        if "7" in term or "ngày" in term.lower():
            return "7d"
        elif "28" in term:
            return "28d"
        elif "56" in term:
            return "56d"
        elif "14" in term:
            return "14d"
        else:
            return term
    
    # ========================================
    # EVENT TRANSFORMERS
    # ========================================
    
    def _transform_news(self, item: Dict[str, Any]) -> Optional[EventRecord]:
        """Transform news item to EventRecord."""
        title = item.get("title", "").strip()
        if not title:
            return None
        
        # Use full_title if available
        full_title = item.get("full_title", title)
        if full_title:
            title = full_title
        
        # Parse published date
        date_str = item.get("date")
        published_at = self._parse_datetime(date_str)
        
        # Determine event type
        categories = item.get("categories", [])
        event_type = EventType.NEWS
        
        # Check if it's a press release or circular
        if any("Thông cáo" in cat for cat in categories):
            event_type = EventType.PRESS_RELEASE
        elif any("Văn bản" in cat for cat in categories):
            event_type = EventType.CIRCULAR
        
        return EventRecord(
            event_type=event_type,
            title=title,
            summary=item.get("summary"),
            content=item.get("content"),
            published_at=published_at,
            source=item.get("source", "SBV"),
            source_url=item.get("source_url"),
            language="vi",
            categories=categories,
            has_full_content=item.get("fetch_success", False),
            attachments=self._parse_attachments(item),
        )
    
    def _parse_attachments(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse attachments from news item."""
        attachments = []
        
        pdf_content = item.get("pdf_content", [])
        if pdf_content:
            for pdf in pdf_content:
                if isinstance(pdf, dict):
                    attachments.append({
                        "url": pdf.get("url"),
                        "type": "pdf",
                        "title": pdf.get("title"),
                    })
        
        return attachments
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _parse_date(self, date_str: Any) -> date:
        """Parse date string to date object."""
        if date_str is None:
            return date.today()
            
        if isinstance(date_str, date):
            return date_str
            
        date_str = str(date_str).strip()
        
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return date.today()
    
    def _parse_datetime(self, dt_str: Any) -> datetime:
        """Parse datetime string to datetime object."""
        if dt_str is None:
            return datetime.now()
            
        if isinstance(dt_str, datetime):
            return dt_str
            
        dt_str = str(dt_str).strip()
        
        # Remove parentheses if present e.g., "(28/01/2026)"
        dt_str = dt_str.strip("()")
        
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse datetime: {dt_str}")
        return datetime.now()
