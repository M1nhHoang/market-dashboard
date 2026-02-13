"""
Event Repository

Handles all database operations for events, causal analyses, and topics.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Sequence

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Event, CausalAnalysis, TopicFrequency, ScoreHistory
from .base import BaseRepository


class EventRepository(BaseRepository[Event]):
    """Repository for event operations."""
    
    model = Event
    
    # ============================================
    # EVENT QUERIES
    # ============================================
    
    async def get_with_analysis(self, event_id: str) -> Optional[Event]:
        """Get event with its causal analysis loaded."""
        stmt = (
            select(Event)
            .options(selectinload(Event.causal_analysis))
            .where(Event.id == event_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_section(
        self,
        section: str,
        limit: int = 50,
        offset: int = 0
    ) -> Sequence[Event]:
        """
        Get events by display section.
        
        Args:
            section: 'key_events', 'other_news', or 'archive'
            limit: Maximum results
            offset: Number to skip
            
        Returns:
            Events sorted by score (key_events) or date (other_news)
        """
        stmt = select(Event).where(Event.display_section == section)
        
        if section == "key_events":
            stmt = stmt.order_by(desc(Event.current_score))
        else:
            stmt = stmt.order_by(desc(Event.published_at))
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_key_events(self, limit: int = 15) -> Sequence[Event]:
        """Get key events sorted by score."""
        return await self.get_by_section("key_events", limit=limit)
    
    async def get_other_news(self, limit: int = 50) -> Sequence[Event]:
        """Get other news sorted by date."""
        return await self.get_by_section("other_news", limit=limit)
    
    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date = None,
        limit: int = 100
    ) -> Sequence[Event]:
        """Get events within a date range."""
        if end_date is None:
            end_date = date.today()
        
        stmt = (
            select(Event)
            .where(
                and_(
                    Event.run_date >= start_date,
                    Event.run_date <= end_date,
                )
            )
            .order_by(desc(Event.current_score))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_category(
        self,
        category: str,
        limit: int = 50
    ) -> Sequence[Event]:
        """Get events by category."""
        stmt = (
            select(Event)
            .where(Event.category == category)
            .order_by(desc(Event.current_score))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_indicator(
        self,
        indicator_id: str,
        limit: int = 50
    ) -> Sequence[Event]:
        """Get events linked to a specific indicator."""
        # JSON contains for SQLite
        stmt = (
            select(Event)
            .where(Event.linked_indicators.contains([indicator_id]))
            .order_by(desc(Event.current_score))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_active_events(
        self,
        max_age_days: int = 30
    ) -> Sequence[Event]:
        """
        Get all active (non-archived) events for ranking.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            All events within age limit
        """
        cutoff_date = date.today() - timedelta(days=max_age_days)
        
        stmt = (
            select(Event)
            .where(
                or_(
                    Event.display_section != "archive",
                    Event.run_date >= cutoff_date,
                )
            )
            .order_by(desc(Event.current_score))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def find_by_hash(self, hash_value: str) -> Optional[Event]:
        """Find event by content hash (for deduplication)."""
        stmt = select(Event).where(Event.hash == hash_value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_recent_titles(
        self,
        source: Optional[str] = None,
        days: int = 7
    ) -> set[str]:
        """
        Get set of recent event titles for deduplication at crawler level.
        
        Args:
            source: Filter by source (e.g., 'sbv', 'cafef'). None = all sources.
            days: How many days back to look (default: 7)
            
        Returns:
            Set of titles (stripped, original case)
        """
        cutoff_date = date.today() - timedelta(days=days)
        
        stmt = select(Event.title).where(Event.run_date >= cutoff_date)
        
        if source:
            stmt = stmt.where(Event.source == source)
        
        result = await self.session.execute(stmt)
        titles = result.scalars().all()
        
        return {t.strip() for t in titles if t}
    
    # ============================================
    # EVENT CREATION
    # ============================================
    
    async def create_event(
        self,
        title: str,
        content: str = None,
        summary: str = None,
        source: str = None,
        source_url: str = None,
        category: str = None,
        region: str = "vietnam",
        is_market_relevant: bool = True,
        linked_indicators: List[str] = None,
        published_at: datetime = None,
        hash_value: str = None,
    ) -> Event:
        """
        Create a new event.
        
        Generates ID automatically if not provided.
        """
        now = self.now()
        
        event = Event(
            id=self.generate_id("evt"),
            title=title,
            content=content,
            summary=summary,
            source=source,
            source_url=source_url,
            category=category,
            region=region,
            is_market_relevant=is_market_relevant,
            linked_indicators=linked_indicators or [],
            published_at=published_at or now,
            run_date=self.today(),
            hash=hash_value,
            created_at=now,
            updated_at=now,
        )
        
        return await self.add(event)
    
    async def update_scores(
        self,
        event_id: str,
        base_score: int,
        score_factors: dict = None,
        current_score: float = None,
        decay_factor: float = 1.0,
        boost_factor: float = 1.0,
        display_section: str = None,
    ) -> Optional[Event]:
        """Update event scoring fields."""
        event = await self.get(event_id)
        if not event:
            return None
        
        event.base_score = base_score
        event.score_factors = score_factors
        event.current_score = current_score or float(base_score)
        event.decay_factor = decay_factor
        event.boost_factor = boost_factor
        event.display_section = display_section
        event.last_ranked_at = self.now()
        event.updated_at = self.now()
        
        return await self.update(event)
    
    # ============================================
    # CAUSAL ANALYSIS
    # ============================================
    
    async def add_causal_analysis(
        self,
        event_id: str,
        template_id: str = None,
        chain_steps: List[dict] = None,
        confidence: str = None,
        needs_investigation: List[str] = None,
        affected_indicators: List[str] = None,
        impact_on_vn: str = None,
        reasoning: str = None,
    ) -> CausalAnalysis:
        """Add causal analysis to an event."""
        now = self.now()
        
        analysis = CausalAnalysis(
            id=self.generate_id("ca"),
            event_id=event_id,
            template_id=template_id,
            chain_steps=chain_steps or [],
            confidence=confidence,
            needs_investigation=needs_investigation or [],
            affected_indicators=affected_indicators or [],
            impact_on_vn=impact_on_vn,
            reasoning=reasoning,
            created_at=now,
            updated_at=now,
        )
        
        self.session.add(analysis)
        await self.session.flush()
        return analysis
    
    async def get_causal_analysis(
        self,
        event_id: str
    ) -> Optional[CausalAnalysis]:
        """Get causal analysis for an event."""
        stmt = select(CausalAnalysis).where(CausalAnalysis.event_id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    # ============================================
    # HOT TOPICS
    # ============================================
    
    async def get_hot_topics(self, limit: int = 10) -> Sequence[TopicFrequency]:
        """Get current hot topics."""
        stmt = (
            select(TopicFrequency)
            .where(TopicFrequency.is_hot == True)
            .order_by(desc(TopicFrequency.occurrence_count))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_topic_frequency(
        self,
        topic: str,
        event_id: str,
        category: str = None
    ) -> TopicFrequency:
        """
        Update topic frequency tracking.
        
        Creates new topic if doesn't exist.
        Updates occurrence count and hot status.
        """
        today = self.today()
        week_ago = today - timedelta(days=7)
        
        # Find existing topic
        stmt = select(TopicFrequency).where(TopicFrequency.topic == topic)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.occurrence_count += 1
            existing.last_seen = today
            
            # Add event to related events
            related = existing.related_event_ids or []
            if event_id not in related:
                related.append(event_id)
            existing.related_event_ids = related
            
            # Check if hot (3+ in 7 days)
            if existing.first_seen and existing.first_seen >= week_ago:
                existing.is_hot = existing.occurrence_count >= 3
            
            await self.session.flush()
            return existing
        else:
            topic_freq = TopicFrequency(
                id=self.generate_id("topic"),
                topic=topic,
                category=category,
                occurrence_count=1,
                first_seen=today,
                last_seen=today,
                related_event_ids=[event_id],
                is_hot=False,
            )
            self.session.add(topic_freq)
            await self.session.flush()
            return topic_freq
    
    # ============================================
    # SCORE HISTORY
    # ============================================
    
    async def add_score_history(
        self,
        event_id: str,
        score: float,
        decay_factor: float,
        boost_factor: float,
        display_section: str,
    ) -> ScoreHistory:
        """Add a score history record for analytics."""
        history = ScoreHistory(
            id=self.generate_id("sh"),
            event_id=event_id,
            score=score,
            decay_factor=decay_factor,
            boost_factor=boost_factor,
            display_section=display_section,
            recorded_at=self.now(),
        )
        self.session.add(history)
        await self.session.flush()
        return history
