"""
Signal Accuracy Stats Repository

Handles all database operations for signal accuracy statistics.
"""
from datetime import date
from typing import Optional

from sqlalchemy import select, and_, desc

from database.models import SignalAccuracyStats
from ..base import BaseRepository


class SignalAccuracyStatsRepository(BaseRepository[SignalAccuracyStats]):
    """Repository for signal accuracy statistics."""
    
    model = SignalAccuracyStats
    
    async def get_latest(
        self,
        period: str = "all_time",
        confidence_level: str = None,
        indicator_id: str = None
    ) -> Optional[SignalAccuracyStats]:
        """Get latest accuracy stats for given filters."""
        conditions = [SignalAccuracyStats.period == period]
        
        if confidence_level:
            conditions.append(SignalAccuracyStats.confidence_level == confidence_level)
        else:
            conditions.append(SignalAccuracyStats.confidence_level.is_(None))
        
        if indicator_id:
            conditions.append(SignalAccuracyStats.indicator_id == indicator_id)
        else:
            conditions.append(SignalAccuracyStats.indicator_id.is_(None))
        
        stmt = (
            select(SignalAccuracyStats)
            .where(and_(*conditions))
            .order_by(desc(SignalAccuracyStats.calculated_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def upsert_stats(
        self,
        period: str,
        total_signals: int,
        verified_correct: int,
        verified_wrong: int,
        expired: int,
        period_start: date = None,
        period_end: date = None,
        confidence_level: str = None,
        indicator_id: str = None,
    ) -> SignalAccuracyStats:
        """Create or update accuracy stats."""
        # Try to find existing
        existing = await self.get_latest(period, confidence_level, indicator_id)
        
        accuracy_rate = None
        total_verified = verified_correct + verified_wrong
        if total_verified > 0:
            accuracy_rate = verified_correct / total_verified
        
        now = self.now()
        
        if existing and existing.period_start == period_start:
            # Update existing
            existing.total_signals = total_signals
            existing.verified_correct = verified_correct
            existing.verified_wrong = verified_wrong
            existing.expired = expired
            existing.accuracy_rate = accuracy_rate
            existing.calculated_at = now
            return await self.update(existing)
        else:
            # Create new
            stats = SignalAccuracyStats(
                id=self.generate_id("sta"),
                period=period,
                period_start=period_start,
                period_end=period_end,
                confidence_level=confidence_level,
                indicator_id=indicator_id,
                total_signals=total_signals,
                verified_correct=verified_correct,
                verified_wrong=verified_wrong,
                expired=expired,
                accuracy_rate=accuracy_rate,
                calculated_at=now,
            )
            return await self.add(stats)
