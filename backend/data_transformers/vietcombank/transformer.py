"""
Vietcombank Transformer - Transform Vietcombank crawler output to CrawlerOutput.

Converts exchange rate data from Vietcombank XML API into MetricRecord format.

For each currency, creates up to 3 metrics:
- {currency}_vnd_vcb_buy: Cash buy rate
- {currency}_vnd_vcb_transfer: Transfer buy rate  
- {currency}_vnd_vcb_sell: Sell rate

The SELL rate is typically the most referenced rate for USD/VND.
"""
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from collections import defaultdict

from data_transformers.base import BaseTransformer
from data_transformers.models import (
    CrawlerOutput,
    MetricRecord,
    MetricType,
)
from .mappings import CURRENCY_MAP, KEY_CURRENCIES, RATE_TYPES


logger = logging.getLogger(__name__)


class VietcombankTransformer(BaseTransformer):
    """
    Transforms Vietcombank crawler output to unified CrawlerOutput.
    
    Input: Raw exchange rate data from VietcombankCrawler
    Output: MetricRecords for each currency rate (buy/transfer/sell)
    
    Key design decisions:
    - Each rate type (buy/transfer/sell) is a separate MetricRecord
    - The sell rate is the primary metric (most commonly referenced)
    - All 3 rates are stored in the attributes dict for context
    - Only key currencies get individual metrics; others grouped
    """
    
    @property
    def source_name(self) -> str:
        return "vietcombank"
    
    def transform(self, raw_data: Dict[str, Any]) -> CrawlerOutput:
        """
        Transform raw Vietcombank crawler data to CrawlerOutput.
        
        Args:
            raw_data: Full raw response from VietcombankCrawler with structure:
                      {"source": "vietcombank", "crawled_at": "...", "data": [...]}
        
        Returns:
            CrawlerOutput with exchange rate metrics (no events or calendar)
        """
        crawled_at = self._parse_datetime(raw_data.get("crawled_at"))
        
        data_items = raw_data.get("data", [])
        if not self.validate_raw_data(data_items):
            return CrawlerOutput(
                source=self.source_name,
                crawled_at=crawled_at,
                success=False,
                error="Empty or invalid data array",
            )
        
        metrics: List[MetricRecord] = []
        stats = defaultdict(int)
        errors = []
        
        for item in data_items:
            item_type = item.get("type")
            
            try:
                if item_type == "metadata":
                    stats.update(item.get("stats", {}))
                    logger.debug(
                        f"[VietcombankTransformer] Raw stats: {item.get('stats', {})}"
                    )
                    continue
                
                if item_type == "exchange_rate":
                    currency_code = item.get("currency_code", "?")
                    if currency_code not in self.TRACKED_CURRENCIES:
                        logger.debug(f"[VietcombankTransformer] Skipping {currency_code} (not tracked)")
                        continue
                    rate_metrics = self._transform_exchange_rate(item)
                    for m in rate_metrics:
                        logger.debug(
                            f"[VietcombankTransformer] Metric → id={m.metric_id} "
                            f"value={m.value} unit={m.unit} date={m.date}"
                        )
                    metrics.extend(rate_metrics)
                    stats["exchange_rate_count"] += len(rate_metrics)
                    
            except Exception as e:
                logger.exception(f"[VietcombankTransformer] Error transforming item: {e}")
                errors.append(str(e))
        
        stats["errors"] = errors
        
        logger.info(
            f"[VietcombankTransformer] Transformed {stats['exchange_rate_count']} "
            f"exchange rate metrics from {len(data_items)} items: "
            f"{[m.metric_id for m in metrics]}"
        )
        
        return CrawlerOutput(
            source=self.source_name,
            crawled_at=crawled_at,
            success=raw_data.get("success", True),
            stats=dict(stats),
            metrics=metrics,
            events=[],      # No news from Vietcombank (rate data only)
            calendar=[],     # No calendar events
        )
    
    # Only these currencies are tracked (as requested)
    TRACKED_CURRENCIES = {"USD", "EUR"}
    
    def _transform_exchange_rate(self, item: Dict[str, Any]) -> List[MetricRecord]:
        """
        Transform a single exchange rate item to MetricRecords.
        
        Only USD and EUR are tracked:
        - USD: sell, buy (cash), transfer  → 3 metrics
        - EUR: sell only                   → 1 metric
        
        Args:
            item: Raw exchange rate data dict
            
        Returns:
            List of MetricRecords
        """
        currency_code = item.get("currency_code", "")
        if currency_code not in self.TRACKED_CURRENCIES:
            return []
        
        buy = item.get("buy")
        transfer = item.get("transfer")
        sell = item.get("sell")
        
        rate_date = self._parse_date(item.get("date"))
        source_url = item.get("source_url", "")
        updated_at_str = item.get("updated_at", "")
        
        currency_info = CURRENCY_MAP.get(currency_code, {})
        metric_id_prefix = currency_info.get(
            "metric_id_prefix",
            f"{currency_code.lower()}_vnd_vcb"
        )
        
        # Common attributes stored on all metrics for UI reference
        common_attrs = {
            "currency_code": currency_code,
            "currency_name": item.get("currency_name", "").strip(),
            "buy": buy,
            "transfer": transfer,
            "sell": sell,
            "updated_at": updated_at_str,
        }
        
        metrics = []
        
        # Sell rate — tracked for both USD and EUR
        if sell is not None:
            metrics.append(MetricRecord(
                metric_type=MetricType.EXCHANGE_RATE,
                metric_id=f"{metric_id_prefix}_sell",
                value=sell,
                unit="VND",
                date=rate_date,
                name=f"{currency_code}/VND Sell (VCB)",
                name_vi=f"Bán {currency_code}/VND (VCB)",
                attributes={**common_attrs, "rate_type": "sell"},
                source="Vietcombank",
                source_url=source_url,
            ))
        
        # Buy (cash) rate — USD only
        if currency_code == "USD" and buy is not None:
            metrics.append(MetricRecord(
                metric_type=MetricType.EXCHANGE_RATE,
                metric_id=f"{metric_id_prefix}_buy",
                value=buy,
                unit="VND",
                date=rate_date,
                name=f"{currency_code}/VND Buy Cash (VCB)",
                name_vi=f"Mua TM {currency_code}/VND (VCB)",
                attributes={**common_attrs, "rate_type": "buy"},
                source="Vietcombank",
                source_url=source_url,
            ))
        
        # Transfer rate — USD only
        if currency_code == "USD" and transfer is not None:
            metrics.append(MetricRecord(
                metric_type=MetricType.EXCHANGE_RATE,
                metric_id=f"{metric_id_prefix}_transfer",
                value=transfer,
                unit="VND",
                date=rate_date,
                name=f"{currency_code}/VND Buy Transfer (VCB)",
                name_vi=f"Mua CK {currency_code}/VND (VCB)",
                attributes={**common_attrs, "rate_type": "transfer"},
                source="Vietcombank",
                source_url=source_url,
            ))
        
        return metrics
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string from crawler output."""
        if not dt_str:
            return datetime.now()
        try:
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            return datetime.now()
    
    def _parse_date(self, date_str: str) -> date:
        """Parse date string to date object."""
        if not date_str:
            return date.today()
        try:
            return date.fromisoformat(date_str)
        except (ValueError, TypeError):
            return date.today()
