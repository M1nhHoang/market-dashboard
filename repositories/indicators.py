"""
Indicator Repository

Handles all database operations for indicators and indicator history.
"""
from datetime import date, datetime
from typing import Optional, List, Sequence

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Indicator, IndicatorHistory
from .base import BaseRepository


class IndicatorRepository(BaseRepository[Indicator]):
    """Repository for indicator operations."""
    
    model = Indicator
    
    # ============================================
    # INDICATOR QUERIES
    # ============================================
    
    async def get_by_category(self, category: str) -> Sequence[Indicator]:
        """Get all indicators in a category."""
        stmt = select(Indicator).where(Indicator.category == category)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_all_grouped(self) -> dict[str, Sequence[Indicator]]:
        """
        Get all indicators grouped by category.
        
        Returns:
            Dict mapping category names to lists of indicators
        """
        all_indicators = await self.get_all(limit=500)
        grouped = {}
        for indicator in all_indicators:
            category = indicator.category or "other"
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(indicator)
        return grouped
    
    async def upsert(
        self,
        indicator_id: str,
        name: str,
        value: float,
        unit: str,
        category: str,
        source: str,
        name_vi: str = None,
        subcategory: str = None,
        source_url: str = None,
        change: float = None,
        change_pct: float = None,
        trend: str = None,
    ) -> Indicator:
        """
        Insert or update an indicator.
        
        If indicator exists, updates its values.
        If not, creates a new indicator.
        """
        now = self.now()
        
        existing = await self.get(indicator_id)
        
        if existing:
            # Update existing
            existing.name = name
            existing.value = value
            existing.unit = unit
            existing.category = category
            existing.source = source
            existing.name_vi = name_vi or existing.name_vi
            existing.subcategory = subcategory or existing.subcategory
            existing.source_url = source_url or existing.source_url
            existing.change = change
            existing.change_pct = change_pct
            existing.trend = trend
            existing.updated_at = now
            return await self.update(existing)
        else:
            # Create new
            indicator = Indicator(
                id=indicator_id,
                name=name,
                name_vi=name_vi,
                value=value,
                unit=unit,
                category=category,
                subcategory=subcategory,
                source=source,
                source_url=source_url,
                change=change,
                change_pct=change_pct,
                trend=trend,
                created_at=now,
                updated_at=now,
            )
            return await self.add(indicator)
    
    # ============================================
    # INDICATOR HISTORY
    # ============================================
    
    async def add_history(
        self,
        indicator_id: str,
        value: float,
        record_date: date,
        source: str = None,
        volume: float = None,
    ) -> Optional[IndicatorHistory]:
        """
        Add indicator history record if value changed.
        
        Prevents duplicates by checking existing records.
        
        Returns:
            Created history record, or None if duplicate
        """
        # Check for existing record with same value on same date
        stmt = select(IndicatorHistory).where(
            and_(
                IndicatorHistory.indicator_id == indicator_id,
                IndicatorHistory.date == record_date,
                IndicatorHistory.value == value,
            )
        )
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            return None  # Duplicate
        
        # Get previous value for change calculation
        previous = await self.get_latest_history(indicator_id)
        previous_value = previous.value if previous else None
        
        change = None
        change_pct = None
        if previous_value is not None and previous_value != 0:
            change = value - previous_value
            change_pct = (change / abs(previous_value)) * 100
        
        history = IndicatorHistory(
            id=self.generate_id("hist"),
            indicator_id=indicator_id,
            value=value,
            previous_value=previous_value,
            change=change,
            change_pct=change_pct,
            volume=volume,
            date=record_date,
            recorded_at=self.now(),
            source=source,
        )
        
        self.session.add(history)
        await self.session.flush()
        return history
    
    async def get_latest_history(
        self,
        indicator_id: str
    ) -> Optional[IndicatorHistory]:
        """Get most recent history record for an indicator."""
        stmt = (
            select(IndicatorHistory)
            .where(IndicatorHistory.indicator_id == indicator_id)
            .order_by(desc(IndicatorHistory.date), desc(IndicatorHistory.recorded_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_history(
        self,
        indicator_id: str,
        days: int = 30,
        limit: int = 100
    ) -> Sequence[IndicatorHistory]:
        """
        Get history for an indicator.
        
        Args:
            indicator_id: Indicator ID
            days: Number of days to look back
            limit: Maximum records to return
            
        Returns:
            List of history records, newest first
        """
        from_date = date.today()
        from datetime import timedelta
        start_date = from_date - timedelta(days=days)
        
        stmt = (
            select(IndicatorHistory)
            .where(
                and_(
                    IndicatorHistory.indicator_id == indicator_id,
                    IndicatorHistory.date >= start_date,
                )
            )
            .order_by(desc(IndicatorHistory.date), desc(IndicatorHistory.recorded_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_trends(
        self,
        indicator_ids: List[str],
        days: int = 7
    ) -> dict[str, dict]:
        """
        Get trend information for multiple indicators.
        
        Returns:
            Dict mapping indicator_id to trend info
        """
        from datetime import timedelta
        start_date = date.today() - timedelta(days=days)
        
        trends = {}
        for indicator_id in indicator_ids:
            stmt = (
                select(IndicatorHistory)
                .where(
                    and_(
                        IndicatorHistory.indicator_id == indicator_id,
                        IndicatorHistory.date >= start_date,
                    )
                )
                .order_by(IndicatorHistory.date)
            )
            result = await self.session.execute(stmt)
            history = result.scalars().all()
            
            if len(history) >= 2:
                first = history[0].value
                last = history[-1].value
                change = last - first if first else 0
                change_pct = (change / abs(first) * 100) if first else 0
                
                if change > 0:
                    trend = "up"
                elif change < 0:
                    trend = "down"
                else:
                    trend = "stable"
                
                trends[indicator_id] = {
                    "trend": trend,
                    "change": change,
                    "change_pct": change_pct,
                    "data_points": len(history),
                }
            else:
                trends[indicator_id] = {
                    "trend": "unknown",
                    "change": 0,
                    "change_pct": 0,
                    "data_points": len(history),
                }
        
        return trends
