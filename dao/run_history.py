"""
Run History Repository

Handles all database operations for run history and calendar events.
"""
from typing import Optional, List, Any

from loguru import logger

from .base import BaseRepository
from .entities import RunHistory, CalendarEvent


class RunHistoryRepository(BaseRepository[RunHistory]):
    """Repository for run history operations."""
    
    TABLE_NAME = "run_history"
    
    def _row_to_entity(self, row: Any) -> RunHistory:
        """Convert database row to RunHistory entity."""
        return RunHistory(
            id=row["id"],
            run_date=row["run_date"],
            run_time=row["run_time"],
            news_count=row["news_count"] or 0,
            events_extracted=row["events_extracted"] or 0,
            events_key=row["events_key"] or 0,
            events_other=row["events_other"] or 0,
            investigations_opened=row["investigations_opened"] or 0,
            investigations_updated=row["investigations_updated"] or 0,
            investigations_resolved=row["investigations_resolved"] or 0,
            summary=row["summary"],
            status=row["status"],
        )
    
    def _row_to_calendar(self, row: Any) -> CalendarEvent:
        """Convert database row to CalendarEvent entity."""
        return CalendarEvent(
            id=row["id"],
            date=row["date"],
            time=row["time"],
            event_name=row["event_name"],
            country=row["country"],
            importance=row["importance"],
            forecast=row["forecast"],
            previous=row["previous"],
            actual=row["actual"],
            created_at=row["created_at"],
        )
    
    # ============================================
    # RUN HISTORY CRUD
    # ============================================
    
    def save_run(
        self,
        run_date: str,
        news_count: int,
        events_extracted: int,
        events_key: int,
        events_other: int,
        investigations_opened: int,
        investigations_updated: int,
        investigations_resolved: int,
        summary: str,
        status: str
    ) -> str:
        """
        Save processing run history.
        
        Args:
            run_date: Date of the run
            news_count: Number of news items processed
            events_extracted: Number of events extracted
            events_key: Number of key events
            events_other: Number of other news
            investigations_opened: New investigations opened
            investigations_updated: Investigations updated
            investigations_resolved: Investigations resolved
            summary: Run summary
            status: Run status (success/partial/failed)
            
        Returns:
            Run ID
        """
        run_id = self._generate_id("run")
        
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO run_history (
                    id, run_date, run_time, news_count, events_extracted,
                    events_key, events_other, investigations_opened,
                    investigations_updated, investigations_resolved,
                    summary, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, run_date, self._now(),
                news_count, events_extracted, events_key, events_other,
                investigations_opened, investigations_updated, investigations_resolved,
                summary, status
            ))
        
        logger.info(f"Saved run history: {run_id} ({status})")
        return run_id
    
    def get_last_run(self) -> Optional[RunHistory]:
        """Get the most recent successful run."""
        cursor = self.db.execute("""
            SELECT * FROM run_history 
            WHERE status = 'success'
            ORDER BY run_time DESC LIMIT 1
        """)
        row = cursor.fetchone()
        return self._row_to_entity(row) if row else None
    
    def get_runs_by_date(self, date: str) -> List[RunHistory]:
        """Get all runs for a specific date."""
        return self.find_where(
            "run_date = ?",
            (date,),
            order_by="run_time DESC"
        )
    
    def get_recent_runs(self, days: int = 7) -> List[RunHistory]:
        """Get runs from recent days."""
        cursor = self.db.execute("""
            SELECT * FROM run_history 
            WHERE run_date >= date('now', ?)
            ORDER BY run_time DESC
        """, (f'-{days} days',))
        return [self._row_to_entity(row) for row in cursor.fetchall()]
    
    def get_run_stats(self, days: int = 30) -> dict:
        """Get aggregate stats for runs."""
        cursor = self.db.execute("""
            SELECT 
                COUNT(*) as total_runs,
                SUM(news_count) as total_news,
                SUM(events_extracted) as total_events,
                SUM(investigations_opened) as total_investigations,
                SUM(investigations_resolved) as total_resolved,
                AVG(events_extracted) as avg_events_per_run
            FROM run_history 
            WHERE run_date >= date('now', ?)
            AND status = 'success'
        """, (f'-{days} days',))
        
        row = cursor.fetchone()
        return {
            "total_runs": row["total_runs"] or 0,
            "total_news": row["total_news"] or 0,
            "total_events": row["total_events"] or 0,
            "total_investigations": row["total_investigations"] or 0,
            "total_resolved": row["total_resolved"] or 0,
            "avg_events_per_run": round(row["avg_events_per_run"] or 0, 1),
        }
    
    # ============================================
    # CALENDAR EVENTS
    # ============================================
    
    def save_calendar_event(
        self,
        date: str,
        event_name: str,
        time: str = None,
        country: str = None,
        importance: str = None,
        forecast: str = None,
        previous: str = None,
        actual: str = None
    ) -> str:
        """Save an economic calendar event."""
        event_id = self._generate_id("cal")
        
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO calendar_events (
                    id, date, time, event_name, country, importance,
                    forecast, previous, actual, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, date, time, event_name, country, importance,
                forecast, previous, actual, self._now()
            ))
        
        return event_id
    
    def get_calendar_events(
        self,
        start_date: str,
        end_date: str = None,
        importance: str = None
    ) -> List[CalendarEvent]:
        """Get calendar events for a date range."""
        end = end_date or start_date
        
        if importance:
            cursor = self.db.execute("""
                SELECT * FROM calendar_events 
                WHERE date BETWEEN ? AND ?
                AND importance = ?
                ORDER BY date, time
            """, (start_date, end, importance))
        else:
            cursor = self.db.execute("""
                SELECT * FROM calendar_events 
                WHERE date BETWEEN ? AND ?
                ORDER BY date, time
            """, (start_date, end))
        
        return [self._row_to_calendar(row) for row in cursor.fetchall()]
    
    def get_upcoming_events(self, days: int = 7) -> List[CalendarEvent]:
        """Get upcoming calendar events."""
        cursor = self.db.execute("""
            SELECT * FROM calendar_events 
            WHERE date BETWEEN date('now') AND date('now', ?)
            ORDER BY date, time
        """, (f'+{days} days',))
        return [self._row_to_calendar(row) for row in cursor.fetchall()]
    
    def update_calendar_actual(
        self,
        event_id: str,
        actual: str
    ) -> bool:
        """Update calendar event with actual value."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "UPDATE calendar_events SET actual = ? WHERE id = ?",
                (actual, event_id)
            )
            return cursor.rowcount > 0
