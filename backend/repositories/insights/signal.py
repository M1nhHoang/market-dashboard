"""
Signal Repository

Handles all database operations for signals.
"""
from datetime import timedelta
from typing import Optional, List, Sequence

from sqlalchemy import select, and_, desc, func

from database.models import Signal
from ..base import BaseRepository


class SignalRepository(BaseRepository[Signal]):
    """Repository for signal operations."""
    
    model = Signal
    
    # ============================================
    # SIGNAL QUERIES
    # ============================================
    
    async def get_active(self, limit: int = 50) -> Sequence[Signal]:
        """Get all active (pending) signals."""
        stmt = (
            select(Signal)
            .where(Signal.status == "active")
            .order_by(
                Signal.confidence.desc(),
                Signal.expires_at.asc()
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: str,
        limit: int = 50
    ) -> Sequence[Signal]:
        """Get signals by status."""
        stmt = (
            select(Signal)
            .where(Signal.status == status)
            .order_by(desc(Signal.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_expired_unverified(self) -> Sequence[Signal]:
        """Get signals that have expired but not verified."""
        now = self.now()
        stmt = (
            select(Signal)
            .where(
                and_(
                    Signal.status == "active",
                    Signal.expires_at <= now
                )
            )
            .order_by(Signal.expires_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_indicator(
        self,
        indicator_id: str,
        active_only: bool = True,
        limit: int = 50
    ) -> Sequence[Signal]:
        """Get signals targeting a specific indicator."""
        conditions = [Signal.target_indicator == indicator_id]
        if active_only:
            conditions.append(Signal.status == "active")
        
        stmt = (
            select(Signal)
            .where(and_(*conditions))
            .order_by(desc(Signal.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_theme(
        self,
        theme_id: str,
        limit: int = 50
    ) -> Sequence[Signal]:
        """Get signals linked to a theme."""
        stmt = (
            select(Signal)
            .where(Signal.theme_id == theme_id)
            .order_by(desc(Signal.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_recent_verified(
        self,
        days: int = 30,
        limit: int = 50
    ) -> Sequence[Signal]:
        """Get recently verified signals."""
        cutoff = self.now() - timedelta(days=days)
        stmt = (
            select(Signal)
            .where(
                and_(
                    Signal.status.in_(["verified_correct", "verified_wrong"]),
                    Signal.verified_at >= cutoff
                )
            )
            .order_by(desc(Signal.verified_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_ids(self, ids: List[str]) -> Sequence[Signal]:
        """Get signals by list of IDs."""
        if not ids:
            return []
        stmt = select(Signal).where(Signal.id.in_(ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    # ============================================
    # SIGNAL CREATION & UPDATE
    # ============================================
    
    async def create_signal(
        self,
        prediction: str,
        source_event_id: str = None,
        direction: str = None,
        target_indicator: str = None,
        target_range_low: float = None,
        target_range_high: float = None,
        confidence: str = "medium",
        timeframe_days: int = None,
        reasoning: str = None,
        theme_id: str = None,
        source_event_ids: List[str] = None,
        related_indicators: List[str] = None,
        expires_at=None,
    ) -> Signal:
        """Create a new signal."""
        now = self.now()
        if expires_at is None and timeframe_days:
            expires_at = now + timedelta(days=timeframe_days)
        
        signal = Signal(
            id=self.generate_id("sig"),
            prediction=prediction,
            direction=direction,
            target_indicator=target_indicator,
            target_range_low=target_range_low,
            target_range_high=target_range_high,
            confidence=confidence,
            timeframe_days=timeframe_days,
            expires_at=expires_at,
            source_event_id=source_event_id,
            source_event_ids=source_event_ids or ([source_event_id] if source_event_id else []),
            reasoning=reasoning,
            theme_id=theme_id,
            status="active",
            created_at=now,
            updated_at=now,
        )
        
        return await self.add(signal)
    
    async def verify(
        self,
        signal_id: str,
        status: str,
        actual_value: float = None,
        accuracy_notes: str = None,
    ) -> Optional[Signal]:
        """Verify a signal as correct, wrong, or expired."""
        signal = await self.get(signal_id)
        if not signal:
            return None
        
        signal.status = status
        signal.actual_value = actual_value
        signal.verified_at = self.now()
        signal.accuracy_notes = accuracy_notes
        signal.updated_at = self.now()
        
        return await self.update(signal)
    
    async def link_to_theme(
        self,
        signal_id: str,
        theme_id: str
    ) -> Optional[Signal]:
        """Link signal to a theme."""
        signal = await self.get(signal_id)
        if not signal:
            return None
        
        signal.theme_id = theme_id
        signal.updated_at = self.now()
        
        return await self.update(signal)
    
    # ============================================
    # ACCURACY STATS
    # ============================================
    
    async def get_accuracy_stats(
        self,
        days: int = 30,
        confidence: str = None,
        indicator_id: str = None
    ) -> dict:
        """Calculate accuracy statistics for signals."""
        cutoff = self.now() - timedelta(days=days)
        
        conditions = [Signal.verified_at >= cutoff]
        if confidence:
            conditions.append(Signal.confidence == confidence)
        if indicator_id:
            conditions.append(Signal.target_indicator == indicator_id)
        
        # Count by status
        stmt = (
            select(
                Signal.status,
                func.count(Signal.id).label('count')
            )
            .where(
                and_(
                    Signal.status.in_(["verified_correct", "verified_wrong", "expired"]),
                    *conditions
                )
            )
            .group_by(Signal.status)
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        stats = {
            "verified_correct": 0,
            "verified_wrong": 0,
            "expired": 0,
        }
        for row in rows:
            stats[row.status] = row.count
        
        total_verified = stats["verified_correct"] + stats["verified_wrong"]
        accuracy_rate = None
        if total_verified > 0:
            accuracy_rate = stats["verified_correct"] / total_verified
        
        return {
            **stats,
            "total_verified": total_verified,
            "accuracy_rate": accuracy_rate,
            "period_days": days,
        }
