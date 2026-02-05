"""
Data Transformer - Transform raw crawler data to database format.

Handles conversion from SBV crawler output to:
1. Indicator updates (current values)
2. Indicator history (time series)
3. News items for LLM classification
"""
import json
from datetime import datetime
from typing import Optional, Any
from pathlib import Path
import hashlib

from loguru import logger

from dao import DatabaseConnection
from constants import (
    INTERBANK_TERM_MAP,
    POLICY_RATE_MAP,
)


class DataTransformer:
    """Transform raw crawler data for database and LLM processing."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def process_sbv_data(self, raw_data: dict) -> dict:
        """
        Process complete SBV crawler output.
        
        Args:
            raw_data: Raw JSON from sbv_crawler
            
        Returns:
            Dict with processed data and stats
        """
        items = raw_data.get('data', [])
        crawled_at = raw_data.get('crawled_at', datetime.now().isoformat())
        
        stats = {
            "indicators_updated": 0,
            "history_saved": 0,
            "news_items": 0
        }
        
        news_items = []
        
        for item in items:
            item_type = item.get('type', '')
            
            if item_type == 'metadata':
                continue  # Skip crawl statistics
            
            if item_type == 'exchange_rate':
                self._process_exchange_rate(item)
                stats["indicators_updated"] += 1
            
            elif item_type == 'gold_price':
                self._process_gold_price(item)
                stats["indicators_updated"] += 1
            
            elif item_type == 'policy_rate':
                self._process_policy_rate(item)
                stats["indicators_updated"] += 1
            
            elif item_type == 'interbank_rate':
                if self._process_interbank_rate(item):
                    stats["history_saved"] += 1
                stats["indicators_updated"] += 1
            
            elif item_type == 'cpi':
                self._process_cpi(item)
                stats["indicators_updated"] += 1
            
            elif item_type == 'omo':
                self._process_omo(item)
                stats["indicators_updated"] += 1
            
            elif item_type == 'news':
                news_item = self._transform_news(item)
                if news_item:
                    news_items.append(news_item)
                    stats["news_items"] += 1
        
        # Aggregate OMO data
        self._aggregate_omo_daily(items)
        
        logger.info(f"Processed SBV data: {stats}")
        
        return {
            "news_items": news_items,
            "stats": stats,
            "crawled_at": crawled_at
        }
    
    # ============================================
    # INDICATOR PROCESSORS
    # ============================================
    
    def _process_exchange_rate(self, item: dict) -> None:
        """Process USD/VND central rate."""
        self.db.indicators.upsert(
            indicator_id="usd_vnd_central",
            name="USD/VND Central Rate",
            name_vi="Tỷ giá trung tâm USD/VND",
            value=item.get('value'),
            unit=item.get('unit', 'VND'),
            category="vietnam_forex",
            subcategory="exchange_rate",
            source=item.get('source', 'SBV'),
            source_url=item.get('source_url')
        )
        
        # Save to history
        self.db.indicators.save_history(
            indicator_id="usd_vnd_central",
            value=item.get('value'),
            date=item.get('date'),
            source=item.get('source', 'SBV')
        )
    
    def _process_gold_price(self, item: dict) -> None:
        """Process gold prices."""
        # Only track main SJC price
        gold_type = item.get('gold_type', '')
        if gold_type == 'SJC' or item.get('organization', '').startswith('CÔNG TY TNHH MTV VÀNG BẠC'):
            buy_price = item.get('buy_price')
            if buy_price:
                # Convert if in "chỉ" unit
                weight_unit = item.get('weight_unit', '').lower()
                if 'chỉ' in weight_unit:
                    # 1 lượng = 10 chỉ
                    buy_price = buy_price * 10
                
                self.db.indicators.upsert(
                    indicator_id="gold_sjc",
                    name="SJC Gold Price",
                    name_vi="Giá vàng SJC",
                    value=buy_price,
                    unit="VND/lượng",
                    category="vietnam_commodity",
                    subcategory="gold",
                    source=item.get('source', 'SBV'),
                    source_url=item.get('source_url')
                )
    
    def _process_policy_rate(self, item: dict) -> None:
        """Process SBV policy rates."""
        rate_type = item.get('rate_type', '').lower()
        
        # Use POLICY_RATE_MAP from constants
        indicator_info = None
        for key, mapping in POLICY_RATE_MAP.items():
            if key in rate_type:
                indicator_info = mapping
                break
        
        if not indicator_info:
            logger.debug(f"Unknown policy rate type: {rate_type}")
            return
        
        self.db.indicators.upsert(
            indicator_id=indicator_info["indicator_id"],
            name=indicator_info["name"],
            name_vi=indicator_info["name_vi"],
            value=item.get('value'),
            unit=item.get('unit', '%'),
            category="vietnam_monetary",
            subcategory="policy_rate",
            source=item.get('source', 'SBV'),
            source_url=item.get('source_url')
        )
    
    def _process_interbank_rate(self, item: dict) -> bool:
        """
        Process interbank rates.
        Returns True if history was saved (value changed).
        """
        term = item.get('term', '')
        indicator_id = INTERBANK_TERM_MAP.get(term)
        
        if not indicator_id:
            logger.debug(f"Unknown interbank term: {term}")
            return False
        
        # Get previous value for change calculation
        prev_entity = self.db.indicators.get(indicator_id)
        prev_value = prev_entity.value if prev_entity else None
        
        # Calculate change
        current_value = item.get('avg_rate')
        change = None
        change_pct = None
        trend = 'stable'
        
        if prev_value is not None and current_value is not None:
            change = current_value - prev_value
            if prev_value != 0:
                change_pct = (change / prev_value) * 100
            
            if change > 0.05:
                trend = 'up'
            elif change < -0.05:
                trend = 'down'
        
        # Update current indicator
        self.db.indicators.upsert(
            indicator_id=indicator_id,
            name=f"Interbank {term}",
            name_vi=f"Lãi suất liên ngân hàng {term}",
            value=current_value,
            unit=item.get('unit_rate', '% năm'),
            category="vietnam_monetary",
            subcategory="interbank",
            source=item.get('source', 'SBV'),
            source_url=item.get('source_url'),
            change=change,
            change_pct=change_pct,
            trend=trend
        )
        
        # Save to history (returns history_id if saved, None if duplicate)
        result = self.db.indicators.save_history(
            indicator_id=indicator_id,
            value=current_value,
            date=item.get('date'),
            source=item.get('source', 'SBV'),
            volume=item.get('volume'),
            previous_value=prev_value
        )
        return result is not None
    
    def _process_cpi(self, item: dict) -> None:
        """Process CPI data."""
        month = item.get('month')
        year = item.get('year')
        mom_change = item.get('mom_change')
        
        if mom_change is not None:
            self.db.indicators.upsert(
                indicator_id="cpi_mom",
                name=f"CPI MoM {month}/{year}",
                name_vi=f"CPI tháng {month}/{year} so với tháng trước",
                value=mom_change,
                unit="%",
                category="vietnam_inflation",
                subcategory="cpi",
                source=item.get('source', 'SBV/GSO'),
                source_url=item.get('source_url')
            )
        
        yoy_change = item.get('yoy_change')
        if yoy_change is not None:
            self.db.indicators.upsert(
                indicator_id="cpi_yoy",
                name=f"CPI YoY {month}/{year}",
                name_vi=f"CPI tháng {month}/{year} so với cùng kỳ",
                value=yoy_change,
                unit="%",
                category="vietnam_inflation",
                subcategory="cpi",
                source=item.get('source', 'SBV/GSO'),
                source_url=item.get('source_url')
            )
        
        core_inflation = item.get('core_inflation')
        if core_inflation is not None:
            self.db.indicators.upsert(
                indicator_id="core_inflation",
                name="Core Inflation",
                name_vi="Lạm phát cơ bản",
                value=core_inflation,
                unit="%",
                category="vietnam_inflation",
                subcategory="cpi",
                source=item.get('source', 'SBV/GSO'),
                source_url=item.get('source_url')
            )
    
    def _process_omo(self, item: dict) -> None:
        """Process single OMO record."""
        # Individual records are processed for context
        # Aggregation is done separately
        pass
    
    def _aggregate_omo_daily(self, items: list[dict]) -> None:
        """
        Aggregate OMO data by date.
        
        Rules:
        - Use only is_total=True rows with term="Tổng cộng"
        - "Mua kỳ hạn" = inject liquidity
        - "Bán kỳ hạn" = withdraw liquidity (may not be available)
        """
        omo_by_date = {}
        
        for item in items:
            if item.get('type') != 'omo':
                continue
            
            if not item.get('is_total'):
                continue
            
            if item.get('term') != 'Tổng cộng':
                continue
            
            date = item.get('date')
            if not date:
                continue
            
            if date not in omo_by_date:
                omo_by_date[date] = {"inject": 0, "withdraw": 0}
            
            trans_type = item.get('transaction_type', '')
            volume = item.get('volume', 0)
            
            if 'Mua kỳ hạn' in trans_type:
                omo_by_date[date]["inject"] += volume
            elif 'Bán kỳ hạn' in trans_type:
                omo_by_date[date]["withdraw"] += volume
        
        # Save aggregated OMO
        for date, data in omo_by_date.items():
            net = data["inject"] - data["withdraw"]
            
            self.db.indicators.upsert(
                indicator_id="omo_net_daily",
                name="OMO Net Daily",
                name_vi="OMO ròng trong ngày",
                value=net,
                unit="Tỷ đồng",
                category="vietnam_monetary",
                subcategory="omo",
                source="SBV",
                source_url="https://sbv.gov.vn/vi/nghiệp-vụ-thị-trường-mở"
            )
            
            self.db.indicators.save_history(
                indicator_id="omo_net_daily",
                value=net,
                date=date,
                source="SBV"
            )
            
            logger.info(f"OMO {date}: inject={data['inject']}, withdraw={data['withdraw']}, net={net}")
    
    # ============================================
    # NEWS TRANSFORMER
    # ============================================
    
    def _transform_news(self, item: dict) -> Optional[dict]:
        """Transform news item for LLM classification."""
        title = item.get('title', '')
        if not title:
            return None
        
        # Generate hash for deduplication
        content = item.get('content', item.get('summary', ''))
        hash_input = f"{title}:{content[:200]}"
        content_hash = hashlib.md5(hash_input.encode()).hexdigest()
        
        return {
            "title": title,
            "summary": item.get('summary', ''),
            "content": content,
            "source": item.get('source', 'SBV'),
            "source_url": item.get('url', item.get('source_url')),
            "date": item.get('date', item.get('publish_date')),
            "published_at": item.get('date', item.get('publish_date')),
            "hash": content_hash,
            "fetch_success": item.get('fetch_success', False)
        }


# ============================================
# UTILITY FUNCTIONS
# ============================================

def load_raw_data(file_path: Path) -> dict:
    """Load raw JSON data from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def prepare_indicators_for_prompt(db: DatabaseConnection) -> str:
    """Prepare current indicators as text for LLM prompt."""
    entities = db.indicators.get_all()
    
    lines = ["Current indicators:"]
    for entity in entities:
        ind = entity.to_dict()
        value = ind.get('value')
        unit = ind.get('unit', '')
        change = ind.get('change')
        trend = ind.get('trend', '')
        
        change_str = ""
        if change is not None:
            sign = "+" if change > 0 else ""
            change_str = f" ({sign}{change:.2f})"
        
        trend_icon = ""
        if trend == 'up':
            trend_icon = " ↑"
        elif trend == 'down':
            trend_icon = " ↓"
        
        lines.append(f"- {ind['name']}: {value} {unit}{change_str}{trend_icon}")
    
    return "\n".join(lines)


def prepare_investigations_for_prompt(db: DatabaseConnection) -> str:
    """Prepare open investigations as text for LLM prompt."""
    entities = db.investigations.get_open()
    
    if not entities:
        return "No open investigations."
    
    lines = ["Open investigations:"]
    for entity in entities:
        inv = entity.to_dict()
        priority_icon = "⚡" if inv.get('priority') == 'high' else "📋"
        lines.append(f"{priority_icon} [{inv['id']}] {inv['question']}")
        if inv.get('evidence_count', 0) > 0:
            lines.append(f"   Evidence: {inv['evidence_count']} items")
        lines.append(f"   Created: {inv.get('created_at', 'unknown')}")
    
    return "\n".join(lines)
