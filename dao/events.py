"""
Event Repository

Handles all database operations for events, causal analyses, and topics.
"""
import json
from typing import Optional, List, Dict, Any

from loguru import logger

from .base import BaseRepository
from .entities import Event, CausalAnalysis, TopicFrequency


class EventRepository(BaseRepository[Event]):
    """Repository for event operations."""
    
    TABLE_NAME = "events"
    
    def _row_to_entity(self, row: Any) -> Event:
        """Convert database row to Event entity."""
        return Event(
            id=row["id"],
            title=row["title"],
            summary=row["summary"],
            content=row["content"],
            source=row["source"],
            source_url=row["source_url"],
            is_market_relevant=bool(row["is_market_relevant"]),
            category=row["category"],
            region=row["region"],
            linked_indicators=self._json_decode(row["linked_indicators"]) or [],
            base_score=row["base_score"],
            score_factors=self._json_decode(row["score_factors"]) or {},
            current_score=row["current_score"],
            decay_factor=row["decay_factor"] or 1.0,
            boost_factor=row["boost_factor"] or 1.0,
            display_section=row["display_section"],
            hot_topic=row["hot_topic"],
            is_follow_up=bool(row["is_follow_up"]),
            follows_up_on=row["follows_up_on"],
            published_at=row["published_at"],
            created_at=row["created_at"],
            run_date=row["run_date"],
            last_ranked_at=row["last_ranked_at"],
            hash=row["hash"],
        )
    
    # ============================================
    # EVENT CRUD
    # ============================================
    
    def create(self, event: Dict[str, Any]) -> str:
        """
        Create a new event.
        
        Args:
            event: Event data dict
            
        Returns:
            Created event ID
        """
        event_id = event.get('id') or self._generate_id("evt")
        now = self._now()
        
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO events (
                    id, title, summary, content, source, source_url,
                    is_market_relevant, category, region, linked_indicators,
                    base_score, score_factors, current_score, decay_factor, boost_factor,
                    display_section, hot_topic, is_follow_up, follows_up_on,
                    published_at, created_at, run_date, hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                event.get('title'),
                event.get('summary'),
                event.get('content'),
                event.get('source'),
                event.get('source_url'),
                event.get('is_market_relevant', True),
                event.get('category'),
                event.get('region'),
                self._json_encode(event.get('linked_indicators', [])),
                event.get('base_score'),
                self._json_encode(event.get('score_factors', {})),
                event.get('current_score') or event.get('base_score'),
                event.get('decay_factor', 1.0),
                event.get('boost_factor', 1.0),
                event.get('display_section'),
                event.get('hot_topic'),
                event.get('is_follow_up', False),
                event.get('follows_up_on'),
                event.get('published_at'),
                now,
                event.get('run_date') or self._today(),
                event.get('hash'),
            ))
        
        logger.debug(f"Created event: {event_id}")
        return event_id
    
    def update(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update event fields.
        
        Args:
            event_id: Event ID
            updates: Dict of fields to update
            
        Returns:
            True if updated
        """
        if not updates:
            return False
        
        # Build SET clause
        set_parts = []
        params = []
        
        for key, value in updates.items():
            if key in ('linked_indicators', 'score_factors'):
                value = self._json_encode(value)
            set_parts.append(f"{key} = ?")
            params.append(value)
        
        params.append(event_id)
        
        with self.db.transaction() as conn:
            cursor = conn.execute(
                f"UPDATE events SET {', '.join(set_parts)} WHERE id = ?",
                params
            )
            return cursor.rowcount > 0
    
    def get_by_hash(self, content_hash: str) -> Optional[Event]:
        """Get event by content hash (for deduplication)."""
        return self.find_one_where("hash = ?", (content_hash,))
    
    # ============================================
    # DISPLAY & RANKING
    # ============================================
    
    def get_by_section(
        self,
        section: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Event]:
        """Get events by display section."""
        return self.find_where(
            "display_section = ?",
            (section,),
            order_by="current_score DESC, published_at DESC",
            limit=limit
        )
    
    def get_key_events(self, limit: int = 10) -> List[Event]:
        """Get key events for dashboard."""
        return self.get_by_section("key_events", limit=limit)
    
    def get_other_news(self, limit: int = 20) -> List[Event]:
        """Get other news for dashboard."""
        return self.get_by_section("other_news", limit=limit)
    
    def get_active_events(self, max_age_days: int = 30) -> List[Event]:
        """Get all active (non-archived) events for ranking."""
        cursor = self.db.execute("""
            SELECT * FROM events 
            WHERE run_date >= date('now', ?)
            AND display_section != 'archive'
            ORDER BY current_score DESC
        """, (f'-{max_age_days} days',))
        return [self._row_to_entity(row) for row in cursor.fetchall()]
    
    def update_ranking(
        self,
        event_id: str,
        current_score: float,
        decay_factor: float,
        boost_factor: float,
        display_section: str,
        hot_topic: str = None
    ) -> None:
        """Update event ranking after Layer 3 processing."""
        with self.db.transaction() as conn:
            conn.execute("""
                UPDATE events SET
                    current_score = ?,
                    decay_factor = ?,
                    boost_factor = ?,
                    display_section = ?,
                    hot_topic = ?,
                    last_ranked_at = ?
                WHERE id = ?
            """, (
                current_score, decay_factor, boost_factor,
                display_section, hot_topic, self._now(), event_id
            ))
    
    def get_by_category(self, category: str, limit: int = 50) -> List[Event]:
        """Get events by category."""
        return self.find_where(
            "category = ?",
            (category,),
            order_by="published_at DESC",
            limit=limit
        )
    
    def get_recent(self, days: int = 7, limit: int = 100) -> List[Event]:
        """Get recent events."""
        cursor = self.db.execute("""
            SELECT * FROM events 
            WHERE run_date >= date('now', ?)
            ORDER BY published_at DESC
            LIMIT ?
        """, (f'-{days} days', limit))
        return [self._row_to_entity(row) for row in cursor.fetchall()]
    
    # ============================================
    # CAUSAL ANALYSIS
    # ============================================
    
    def create_causal_analysis(self, analysis: Dict[str, Any]) -> str:
        """Create causal analysis for an event."""
        analysis_id = self._generate_id("ca")
        
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO causal_analyses (
                    id, event_id, template_id, chain_steps, confidence,
                    needs_investigation, affected_indicators, impact_on_vn,
                    reasoning, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_id,
                analysis.get('event_id'),
                analysis.get('template_id'),
                self._json_encode(analysis.get('chain_steps', [])),
                analysis.get('confidence'),
                self._json_encode(analysis.get('needs_investigation', [])),
                self._json_encode(analysis.get('affected_indicators', [])),
                analysis.get('impact_on_vn'),
                analysis.get('reasoning'),
                self._now(),
            ))
        
        return analysis_id
    
    def get_causal_analysis(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get causal analysis for an event."""
        cursor = self.db.execute(
            "SELECT * FROM causal_analyses WHERE event_id = ?",
            (event_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row["id"],
            "event_id": row["event_id"],
            "template_id": row["template_id"],
            "chain_steps": self._json_decode(row["chain_steps"]),
            "confidence": row["confidence"],
            "needs_investigation": self._json_decode(row["needs_investigation"]),
            "affected_indicators": self._json_decode(row["affected_indicators"]),
            "impact_on_vn": row["impact_on_vn"],
            "reasoning": row["reasoning"],
            "created_at": row["created_at"],
        }
    
    # ============================================
    # TOPIC TRACKING
    # ============================================
    
    def update_topic_frequency(
        self,
        topic: str,
        category: str,
        event_id: str
    ) -> None:
        """Update topic frequency tracking."""
        today = self._today()
        
        with self.db.transaction() as conn:
            # Check if topic exists
            cursor = conn.execute(
                "SELECT id, occurrence_count, related_event_ids FROM topic_frequency WHERE topic = ?",
                (topic,)
            )
            row = cursor.fetchone()
            
            if row:
                event_ids = self._json_decode(row['related_event_ids']) or []
                event_ids.append(event_id)
                conn.execute("""
                    UPDATE topic_frequency SET
                        occurrence_count = occurrence_count + 1,
                        last_seen = ?,
                        related_event_ids = ?,
                        is_hot = (occurrence_count + 1) >= 3
                    WHERE id = ?
                """, (today, self._json_encode(event_ids), row['id']))
            else:
                topic_id = self._generate_id("topic")
                conn.execute("""
                    INSERT INTO topic_frequency (
                        id, topic, category, occurrence_count, first_seen, 
                        last_seen, related_event_ids, is_hot
                    ) VALUES (?, ?, ?, 1, ?, ?, ?, FALSE)
                """, (topic_id, topic, category, today, today, self._json_encode([event_id])))
    
    def get_hot_topics(self, days: int = 7) -> List[TopicFrequency]:
        """Get hot topics from recent days."""
        cursor = self.db.execute("""
            SELECT * FROM topic_frequency 
            WHERE is_hot = TRUE 
            AND last_seen >= date('now', ?)
            ORDER BY occurrence_count DESC
        """, (f'-{days} days',))
        
        return [TopicFrequency(
            id=row["id"],
            topic=row["topic"],
            category=row["category"],
            occurrence_count=row["occurrence_count"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            related_event_ids=self._json_decode(row["related_event_ids"]) or [],
            is_hot=bool(row["is_hot"]),
        ) for row in cursor.fetchall()]
    
    # ============================================
    # SCORE HISTORY
    # ============================================
    
    def save_score_history(
        self,
        event_id: str,
        score: float,
        decay_factor: float,
        boost_factor: float,
        display_section: str
    ) -> None:
        """Save score snapshot for analysis."""
        history_id = self._generate_id("sh")
        
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO score_history (
                    id, event_id, score, decay_factor, boost_factor,
                    display_section, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                history_id, event_id, score, decay_factor,
                boost_factor, display_section, self._now()
            ))
