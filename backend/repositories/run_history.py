"""
Run History Repository

Handles all database operations for pipeline run history and calendar events.
"""
from datetime import date, datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RunHistory, CalendarEvent
from .base import BaseRepository


class RunHistoryRepository(BaseRepository[RunHistory]):
    """Repository for run history operations."""
    
    model = RunHistory
    
    # ============================================
    # RUN HISTORY
    # ============================================
    
    async def get_latest(self) -> Optional[RunHistory]:
        """Get the most recent run."""
        stmt = (
            select(RunHistory)
            .order_by(desc(RunHistory.run_time))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_date(self, run_date: date) -> Sequence[RunHistory]:
        """Get all runs for a specific date."""
        stmt = (
            select(RunHistory)
            .where(RunHistory.run_date == run_date)
            .order_by(desc(RunHistory.run_time))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_recent(self, days: int = 7) -> Sequence[RunHistory]:
        """Get runs from the last N days."""
        cutoff = date.today() - timedelta(days=days)
        
        stmt = (
            select(RunHistory)
            .where(RunHistory.run_date >= cutoff)
            .order_by(desc(RunHistory.run_time))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def create_run(
        self,
        news_count: int = 0,
        events_extracted: int = 0,
        events_key: int = 0,
        events_other: int = 0,
        signals_created: int = 0,
        themes_updated: int = 0,
        watchlist_triggered: int = 0,
        summary: str = None,
        status: str = "success",
    ) -> RunHistory:
        """Create a new run history record."""
        now = self.now()
        today = self.today()
        
        run = RunHistory(
            id=self.generate_id("run"),
            run_date=today,
            run_time=now,
            news_count=news_count,
            events_extracted=events_extracted,
            events_key=events_key,
            events_other=events_other,
            signals_created=signals_created,
            themes_updated=themes_updated,
            watchlist_triggered=watchlist_triggered,
            summary=summary,
            status=status,
        )
        
        return await self.add(run)
    
    async def update_run(
        self,
        run_id: str,
        **kwargs
    ) -> Optional[RunHistory]:
        """Update an existing run record."""
        run = await self.get(run_id)
        if not run:
            return None
        
        for key, value in kwargs.items():
            if hasattr(run, key):
                setattr(run, key, value)
        
        return await self.update(run)
    
    # ============================================
    # CALENDAR EVENTS
    # ============================================
    
    async def get_upcoming_calendar_events(
        self,
        days: int = 7,
        limit: int = 20
    ) -> Sequence[CalendarEvent]:
        """Get upcoming calendar events."""
        today = self.today()
        end_date = today + timedelta(days=days)
        
        stmt = (
            select(CalendarEvent)
            .where(
                CalendarEvent.date >= today,
                CalendarEvent.date <= end_date,
            )
            .order_by(CalendarEvent.date, CalendarEvent.time)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_calendar_events_by_date(
        self,
        event_date: date
    ) -> Sequence[CalendarEvent]:
        """Get calendar events for a specific date."""
        stmt = (
            select(CalendarEvent)
            .where(CalendarEvent.date == event_date)
            .order_by(CalendarEvent.time)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def add_calendar_event(
        self,
        event_name: str,
        event_date: date,
        event_time=None,
        country: str = None,
        importance: str = "medium",
        forecast: str = None,
        previous: str = None,
    ) -> CalendarEvent:
        """Add a new calendar event."""
        from datetime import time as dt_time
        
        event = CalendarEvent(
            id=self.generate_id("cal"),
            event_name=event_name,
            date=event_date,
            time=event_time,
            country=country,
            importance=importance,
            forecast=forecast,
            previous=previous,
            created_at=self.now(),
        )
        
        self.session.add(event)
        await self.session.flush()
        return event
    
    async def update_calendar_actual(
        self,
        event_id: str,
        actual: str
    ) -> Optional[CalendarEvent]:
        """Update calendar event with actual value."""
        stmt = select(CalendarEvent).where(CalendarEvent.id == event_id)
        result = await self.session.execute(stmt)
        event = result.scalar_one_or_none()
        
        if not event:
            return None
        
        event.actual = actual
        await self.session.flush()
        return event
