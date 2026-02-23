"""
Theme Repository

Handles all database operations for themes.

## TREND SYSTEM (migration 005)
This repository now includes methods for the unified "Trends" view:
- get_trends_summary(): Dashboard stats
- get_trends_with_signals(): Main trends query with ordering by urgency
- get_by_urgency(): Filter by urgency level
- recompute_trend_stats(): Update computed fields when signals change
- update_narrative(): Set AI-generated narrative
"""
from datetime import timedelta
from typing import Optional, List, Sequence

from sqlalchemy import select, desc, Integer
from sqlalchemy.orm import selectinload

from database.models import Theme
from ..base import BaseRepository


class ThemeRepository(BaseRepository[Theme]):
    """Repository for theme operations."""
    
    model = Theme
    
    # ============================================
    # THEME QUERIES
    # ============================================
    
    async def get_active(self, limit: int = 20) -> Sequence[Theme]:
        """Get active themes (strength >= 5.0)."""
        stmt = (
            select(Theme)
            .where(Theme.status == "active")
            .order_by(desc(Theme.strength))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_emerging(self, limit: int = 20) -> Sequence[Theme]:
        """Get emerging themes (2.0 <= strength < 5.0)."""
        stmt = (
            select(Theme)
            .where(Theme.status == "emerging")
            .order_by(desc(Theme.strength))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_active_and_emerging(self, limit: int = 30) -> Sequence[Theme]:
        """Get both active and emerging themes."""
        stmt = (
            select(Theme)
            .where(Theme.status.in_(["active", "emerging"]))
            .order_by(desc(Theme.strength))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: str,
        limit: int = 50
    ) -> Sequence[Theme]:
        """Get themes by status."""
        stmt = (
            select(Theme)
            .where(Theme.status == status)
            .order_by(desc(Theme.strength))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_fading(self, limit: int = 20) -> Sequence[Theme]:
        """Get fading themes."""
        stmt = (
            select(Theme)
            .where(Theme.status == "fading")
            .order_by(desc(Theme.last_seen))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def find_by_name(self, name: str) -> Optional[Theme]:
        """Find theme by name (case-insensitive partial match)."""
        stmt = (
            select(Theme)
            .where(Theme.name.ilike(f"%{name}%"))
            .order_by(desc(Theme.strength))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Theme]:
        """Get theme by exact name."""
        stmt = (
            select(Theme)
            .where(Theme.name == name)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_ids(self, ids: List[str]) -> Sequence[Theme]:
        """Get themes by list of IDs."""
        if not ids:
            return []
        stmt = select(Theme).where(Theme.id.in_(ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_with_signals(self, theme_id: str) -> Optional[Theme]:
        """Get theme with all signals loaded."""
        stmt = (
            select(Theme)
            .options(selectinload(Theme.signals))
            .where(Theme.id == theme_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    # ============================================
    # THEME CREATION & UPDATE
    # ============================================
    
    async def create_theme(
        self,
        name: str,
        name_vi: str = None,
        description: str = None,
        event_id: str = None,
        related_event_ids: List[str] = None,
        related_indicators: List[str] = None,
        template_id: str = None,
        initial_strength: float = 1.0,
    ) -> Theme:
        """Create a new theme."""
        now = self.now()
        
        # Build event list
        if related_event_ids is None:
            related_event_ids = []
        if event_id and event_id not in related_event_ids:
            related_event_ids.append(event_id)
        
        theme = Theme(
            id=self.generate_id("thm"),
            name=name,
            name_vi=name_vi,
            description=description,
            related_event_ids=related_event_ids,
            related_signal_ids=[],
            related_indicators=related_indicators or [],
            event_count=len(related_event_ids) if related_event_ids else 1,
            strength=initial_strength,
            first_seen=now,
            last_seen=now,
            status="emerging",
            template_id=template_id,
            created_at=now,
            updated_at=now,
        )
        
        return await self.add(theme)
    
    async def add_event(
        self,
        theme_id: str,
        event_id: str
    ) -> Optional[Theme]:
        """Add an event to a theme."""
        theme = await self.get(theme_id)
        if not theme:
            return None
        
        event_ids = theme.related_event_ids or []
        if event_id not in event_ids:
            event_ids.append(event_id)
            theme.related_event_ids = event_ids
            theme.event_count = len(event_ids)
            theme.last_seen = self.now()
            theme.updated_at = self.now()
        
        return await self.update(theme)
    
    async def add_signal(
        self,
        theme_id: str,
        signal_id: str
    ) -> Optional[Theme]:
        """Add a signal to a theme."""
        theme = await self.get(theme_id)
        if not theme:
            return None
        
        signal_ids = theme.related_signal_ids or []
        if signal_id not in signal_ids:
            signal_ids.append(signal_id)
            theme.related_signal_ids = signal_ids
            theme.updated_at = self.now()
        
        return await self.update(theme)
    
    async def update_strength(
        self,
        theme_id: str,
        strength: float,
        peak_strength: float = None,
        status: str = None,
    ) -> Optional[Theme]:
        """Update theme strength and status."""
        theme = await self.get(theme_id)
        if not theme:
            return None
        
        theme.strength = strength
        if peak_strength is not None:
            theme.peak_strength = peak_strength
        if status:
            theme.status = status
        theme.updated_at = self.now()
        
        return await self.update(theme)
    
    async def archive(self, theme_id: str) -> Optional[Theme]:
        """Archive a theme."""
        return await self.update_strength(theme_id, strength=0.0, status="archived")
    
    # ============================================
    # TREND SYSTEM METHODS
    # Added for unified Trends view (combines themes + signals)
    # ============================================
    
    async def get_trends_summary(self) -> dict:
        """
        Get summary statistics for Trends dashboard.
        
        Used by: GET /api/trends (with_summary=true)
        Returns: {total, urgent_count, watching_count, with_signals_count, signals_accuracy, ...}
        """
        from sqlalchemy import func, and_
        from database.models import Signal
        
        # Count themes by urgency
        stmt_counts = select(
            func.count(Theme.id).label('total'),
            func.sum(func.cast(Theme.urgency == 'urgent', Integer)).label('urgent_count'),
            func.sum(func.cast(Theme.urgency == 'watching', Integer)).label('watching_count'),
            func.sum(func.cast(Theme.signals_count > 0, Integer)).label('with_signals_count'),
        ).where(Theme.status.in_(['active', 'emerging']))
        
        result = await self.session.execute(stmt_counts)
        counts = result.one()
        
        # Get overall signal accuracy
        stmt_accuracy = select(
            func.sum(Signal.status == 'verified_correct').label('correct'),
            func.count(Signal.id).label('verified_total')
        ).where(Signal.status.in_(['verified_correct', 'verified_wrong']))
        
        result_acc = await self.session.execute(stmt_accuracy)
        acc = result_acc.one()
        
        accuracy_pct = None
        if acc.verified_total and acc.verified_total > 0:
            accuracy_pct = round((acc.correct or 0) / acc.verified_total * 100, 1)
        
        return {
            'total': counts.total or 0,
            'urgent_count': counts.urgent_count or 0,
            'watching_count': counts.watching_count or 0,
            'with_signals_count': counts.with_signals_count or 0,
            'signals_correct': acc.correct or 0,
            'signals_total_verified': acc.verified_total or 0,
            'signals_accuracy': accuracy_pct,
        }
    
    async def get_by_urgency(
        self, 
        urgency: str, 
        limit: int = 20
    ) -> Sequence[Theme]:
        """
        Get themes by urgency level.
        
        Used by: GET /api/trends?urgency=urgent
        urgency: 'urgent', 'watching', or 'low'
        """
        stmt = (
            select(Theme)
            .where(Theme.urgency == urgency)
            .where(Theme.status.in_(['active', 'emerging']))
            .order_by(Theme.earliest_signal_expires.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_trends_with_signals(
        self, 
        limit: int = 30,
        include_fading: bool = False
    ) -> Sequence[Theme]:
        """
        Get themes ordered for Trends dashboard.
        
        Used by: GET /api/trends (main endpoint)
        Order: urgent first (by expiry), then watching, then by strength
        """
        from sqlalchemy import case
        
        statuses = ['active', 'emerging']
        if include_fading:
            statuses.append('fading')
        
        # Order: urgent (asc by expiry) > watching > low > no urgency > by strength
        urgency_order = case(
            (Theme.urgency == 'urgent', 1),
            (Theme.urgency == 'watching', 2),
            (Theme.urgency == 'low', 3),
            else_=4
        )
        
        stmt = (
            select(Theme)
            .options(selectinload(Theme.signals))
            .where(Theme.status.in_(statuses))
            .order_by(
                urgency_order,
                Theme.earliest_signal_expires.asc().nullslast(),
                desc(Theme.strength)
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def recompute_trend_stats(self, theme_id: str) -> Optional[Theme]:
        """
        Recompute all trend statistics for a theme.
        
        Called when:
        - Signal is added to theme
        - Signal is verified (correct/wrong)
        - Signal expires
        
        Updates: urgency, earliest_signal_expires, signals_count, signals_accuracy
        """
        from sqlalchemy import func, and_
        from database.models import Signal
        from datetime import timedelta
        
        theme = await self.get(theme_id)
        if not theme:
            return None
        
        now = self.now()
        
        # Count active signals
        stmt_count = select(func.count(Signal.id)).where(
            and_(
                Signal.theme_id == theme_id,
                Signal.status == 'active'
            )
        )
        result = await self.session.execute(stmt_count)
        signals_count = result.scalar() or 0
        
        # Get earliest expiry
        stmt_expiry = select(func.min(Signal.expires_at)).where(
            and_(
                Signal.theme_id == theme_id,
                Signal.status == 'active',
                Signal.expires_at.isnot(None)
            )
        )
        result = await self.session.execute(stmt_expiry)
        earliest_expires = result.scalar()
        
        # Compute urgency
        urgency = None
        if earliest_expires:
            days_until = (earliest_expires - now).days
            if days_until < 7:
                urgency = 'urgent'
            elif days_until < 14:
                urgency = 'watching'
            else:
                urgency = 'low'
        
        # Count verified signals
        stmt_verified = select(
            func.count(Signal.id).label('total'),
            func.sum(func.cast(Signal.status == 'verified_correct', Integer)).label('correct')
        ).where(
            and_(
                Signal.theme_id == theme_id,
                Signal.status.in_(['verified_correct', 'verified_wrong'])
            )
        )
        result = await self.session.execute(stmt_verified)
        verified = result.one()
        
        verified_count = verified.total or 0
        correct_count = verified.correct or 0
        accuracy = None
        if verified_count > 0:
            accuracy = correct_count / verified_count
        
        # Update theme
        theme.signals_count = signals_count
        theme.earliest_signal_expires = earliest_expires
        theme.urgency = urgency
        theme.signals_verified_count = verified_count
        theme.signals_correct_count = correct_count
        theme.signals_accuracy = accuracy
        theme.updated_at = now
        
        return await self.update(theme)
    
    async def update_narrative(
        self,
        theme_id: str,
        narrative: str
    ) -> Optional[Theme]:
        """
        Update the synthesized narrative for a theme.
        
        Used by: LLM pipeline when adding signals to theme
        narrative: AI-generated summary of all signal reasonings
        """
        theme = await self.get(theme_id)
        if not theme:
            return None
        
        theme.narrative = narrative
        theme.updated_at = self.now()
        
        return await self.update(theme)
