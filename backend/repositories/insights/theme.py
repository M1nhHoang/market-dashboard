"""
Theme Repository

Handles all database operations for themes.
"""
from datetime import timedelta
from typing import Optional, List, Sequence

from sqlalchemy import select, desc
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
