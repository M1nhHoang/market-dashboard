"""
Watchlist Repository

Handles all database operations for watchlist items.
"""
from datetime import date, timedelta
from typing import Optional, List, Sequence

from sqlalchemy import select, and_, or_, desc

from database.models import Watchlist
from ..base import BaseRepository
from .utils import parse_condition


class WatchlistRepository(BaseRepository[Watchlist]):
    """Repository for watchlist operations."""
    
    model = Watchlist
    
    # ============================================
    # WATCHLIST QUERIES
    # ============================================
    
    async def get_active(self, limit: int = 50) -> Sequence[Watchlist]:
        """Get all active watchlist items."""
        now = self.now()
        stmt = (
            select(Watchlist)
            .where(
                and_(
                    Watchlist.status == "watching",
                    or_(
                        Watchlist.snoozed_until.is_(None),
                        Watchlist.snoozed_until <= now
                    )
                )
            )
            .order_by(Watchlist.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_triggered(self, limit: int = 50) -> Sequence[Watchlist]:
        """Get triggered watchlist items."""
        stmt = (
            select(Watchlist)
            .where(Watchlist.status == "triggered")
            .order_by(desc(Watchlist.triggered_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: str,
        limit: int = 50
    ) -> Sequence[Watchlist]:
        """Get watchlist items by status."""
        stmt = (
            select(Watchlist)
            .where(Watchlist.status == status)
            .order_by(desc(Watchlist.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_trigger_type(
        self,
        trigger_type: str,
        active_only: bool = True,
        limit: int = 50
    ) -> Sequence[Watchlist]:
        """Get watchlist items by trigger type."""
        conditions = [Watchlist.trigger_type == trigger_type]
        if active_only:
            conditions.append(Watchlist.status == "watching")
        
        stmt = (
            select(Watchlist)
            .where(and_(*conditions))
            .order_by(Watchlist.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_date_triggers(
        self,
        from_date: date = None,
        to_date: date = None,
    ) -> Sequence[Watchlist]:
        """Get date-based triggers in a date range."""
        from_date = from_date or date.today()
        to_date = to_date or from_date + timedelta(days=30)
        
        stmt = (
            select(Watchlist)
            .where(
                and_(
                    Watchlist.trigger_type == "date",
                    Watchlist.status == "watching",
                    Watchlist.trigger_date >= from_date,
                    Watchlist.trigger_date <= to_date,
                )
            )
            .order_by(Watchlist.trigger_date)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_indicator_triggers(
        self,
        indicator_id: str = None
    ) -> Sequence[Watchlist]:
        """Get indicator-based triggers, optionally filtered by indicator."""
        conditions = [
            Watchlist.trigger_type == "indicator",
            Watchlist.status == "watching"
        ]
        if indicator_id:
            conditions.append(Watchlist.trigger_indicator == indicator_id)
        
        stmt = (
            select(Watchlist)
            .where(and_(*conditions))
            .order_by(Watchlist.created_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_keyword_triggers(self) -> Sequence[Watchlist]:
        """Get all keyword-based triggers."""
        stmt = (
            select(Watchlist)
            .where(
                and_(
                    Watchlist.trigger_type == "keyword",
                    Watchlist.status == "watching"
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    # ============================================
    # WATCHLIST CREATION & UPDATE
    # ============================================
    
    async def create_watchlist_item(
        self,
        name: str,
        trigger_type: str,
        description: str = None,
        trigger_indicator: str = None,
        trigger_condition: str = None,
        trigger_keywords: List[str] = None,
        trigger_date: date = None,
        source: str = "user",
        template_id: str = None,
        related_indicators: List[str] = None,
        related_theme_id: str = None,
        created_by: str = "system",
    ) -> Watchlist:
        """Create a new watchlist item."""
        now = self.now()
        
        item = Watchlist(
            id=self.generate_id("wtc"),
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_indicator=trigger_indicator,
            trigger_condition=trigger_condition,
            trigger_keywords=trigger_keywords,
            trigger_date=trigger_date,
            source=source,
            template_id=template_id,
            related_indicators=related_indicators,
            related_theme_id=related_theme_id,
            status="watching",
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        
        return await self.add(item)
    
    async def trigger(
        self,
        item_id: str,
        triggered_by_event_id: str = None,
        trigger_value: float = None,
    ) -> Optional[Watchlist]:
        """Mark a watchlist item as triggered."""
        item = await self.get(item_id)
        if not item:
            return None
        
        item.status = "triggered"
        item.triggered_at = self.now()
        item.triggered_by_event_id = triggered_by_event_id
        item.trigger_value = trigger_value
        item.updated_at = self.now()
        
        return await self.update(item)
    
    async def dismiss(self, item_id: str) -> Optional[Watchlist]:
        """Dismiss a triggered watchlist item."""
        item = await self.get(item_id)
        if not item:
            return None
        
        item.status = "dismissed"
        item.updated_at = self.now()
        
        return await self.update(item)
    
    async def snooze(
        self,
        item_id: str,
        days: int = 7
    ) -> Optional[Watchlist]:
        """Snooze a watchlist item for specified days."""
        item = await self.get(item_id)
        if not item:
            return None
        
        item.status = "watching"  # Reset to watching
        item.snoozed_until = self.now() + timedelta(days=days)
        item.updated_at = self.now()
        
        return await self.update(item)
    
    async def restore(self, item_id: str) -> Optional[Watchlist]:
        """Restore a dismissed watchlist item."""
        item = await self.get(item_id)
        if not item:
            return None
        
        item.status = "watching"
        item.triggered_at = None
        item.triggered_by_event_id = None
        item.trigger_value = None
        item.snoozed_until = None
        item.updated_at = self.now()
        
        return await self.update(item)
    
    # ============================================
    # TRIGGER CHECKING
    # ============================================
    
    async def check_indicator_trigger(
        self,
        item_id: str,
        indicator_repo=None
    ) -> bool:
        """Check if an indicator trigger condition is met."""
        item = await self.get(item_id)
        if not item or item.trigger_type != "indicator" or not item.trigger_condition:
            return False
        
        if not indicator_repo or not item.trigger_indicator:
            return False
        
        # Get current indicator value
        indicator = await indicator_repo.get(item.trigger_indicator)
        if not indicator or indicator.value is None:
            return False
        
        op_func, threshold = parse_condition(item.trigger_condition)
        return op_func(indicator.value, threshold)
    
    async def check_keyword_trigger(
        self,
        item: Watchlist,
        text: str
    ) -> bool:
        """Check if keywords are found in text."""
        if item.trigger_type != "keyword" or not item.trigger_keywords:
            return False
        
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in item.trigger_keywords)
