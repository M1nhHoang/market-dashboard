"""
Context Builder - Build previous context for LLM processing
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from typing import Optional

from loguru import logger


class ContextBuilder:
    """
    Builds context from previous runs to provide continuity to LLM.
    
    Context includes:
    - Last run summary
    - Open investigations
    - Recurring topics
    - Recent predictions
    - Key events from lookback period
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def build_previous_context(self, lookback_days: int = 7) -> dict:
        """
        Build comprehensive context from previous runs.
        
        Args:
            lookback_days: Number of days to look back for context
            
        Returns:
            Dictionary containing all context components
        """
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        context = {
            "last_run_summary": self._get_last_run_summary(),
            "open_investigations": self._get_open_investigations(),
            "recurring_topics": self._get_recurring_topics(lookback_days),
            "recent_predictions": self._get_recent_predictions(lookback_days),
            "key_events_last_period": self._get_key_events(cutoff_str),
            "indicator_trends": self._get_indicator_trends(lookback_days),
            "context_generated_at": datetime.now().isoformat(),
            "lookback_days": lookback_days
        }
        
        logger.info(f"Built context with {len(context['open_investigations'])} open investigations, "
                   f"{len(context['recurring_topics'])} recurring topics, "
                   f"{len(context['indicator_trends'])} indicators")
        
        return context
    
    def _get_last_run_summary(self) -> Optional[str]:
        """Get summary from the most recent processing run."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT summary, run_date, run_time
                FROM run_history
                WHERE status = 'success'
                ORDER BY run_time DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "summary": row["summary"],
                    "run_date": row["run_date"],
                    "run_time": row["run_time"]
                }
            return None
        except Exception as e:
            logger.warning(f"Failed to get last run summary: {e}")
            return None
    
    def _get_open_investigations(self) -> list[dict]:
        """Get all open investigation items."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT 
                    i.id,
                    i.item,
                    i.source_event_id,
                    i.created_at,
                    i.run_date,
                    e.title as source_event_title
                FROM investigations i
                LEFT JOIN events e ON i.source_event_id = e.id
                WHERE i.status IN ('open', 'updated')
                ORDER BY 
                    CASE i.priority 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        ELSE 3 
                    END,
                    i.created_at DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to get open investigations: {e}")
            return []
    
    def _get_recurring_topics(self, lookback_days: int) -> list[dict]:
        """Get topics that appear frequently (importance signal)."""
        try:
            cutoff = datetime.now() - timedelta(days=lookback_days)
            cutoff_str = cutoff.strftime("%Y-%m-%d")
            
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT 
                    topic,
                    category,
                    occurrence_count,
                    first_seen,
                    last_seen,
                    is_hot
                FROM topic_frequency
                WHERE last_seen >= ? AND (occurrence_count >= 3 OR is_hot = TRUE)
                ORDER BY occurrence_count DESC
                LIMIT 20
            """, (cutoff_str,))
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to get recurring topics: {e}")
            return []
    
    def _get_recent_predictions(self, lookback_days: int) -> list[dict]:
        """Get predictions that need verification."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT 
                    id, prediction, confidence, check_by_date,
                    verification_indicator, status
                FROM predictions
                WHERE status = 'pending' 
                AND check_by_date <= date('now', '+7 days')
                ORDER BY check_by_date ASC
                LIMIT 10
            """)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to get recent predictions: {e}")
            return []
    
    def _get_key_events(self, cutoff_date: str) -> list[dict]:
        """Get important events from the lookback period."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT 
                    e.id,
                    e.title,
                    e.summary,
                    e.category,
                    e.region,
                    e.base_score,
                    e.current_score,
                    e.display_section,
                    e.published_at,
                    e.linked_indicators,
                    ca.template_id,
                    ca.confidence
                FROM events e
                LEFT JOIN causal_analyses ca ON e.id = ca.event_id
                WHERE e.run_date >= ? 
                AND e.display_section IN ('key_events', 'other_news')
                ORDER BY e.current_score DESC, e.published_at DESC
                LIMIT 50
            """, (cutoff_date,))
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to get key events: {e}")
            return []
    
    def _get_indicator_trends(self, days: int = 7) -> list[dict]:
        """Get indicator trends from the last N days."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT 
                    id, name, name_vi, category, value, unit,
                    change, change_pct, trend, updated_at
                FROM indicators
                WHERE updated_at >= datetime('now', ?)
                ORDER BY category, name
            """, (f'-{days} days',))
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to get indicator trends: {e}")
            return []
    
    def format_for_prompt(self, context: dict) -> str:
        """Format context dictionary into text for LLM prompt."""
        sections = []
        
        # Last run summary
        if context.get("last_run_summary"):
            run = context["last_run_summary"]
            sections.append(f"### Tóm tắt lần chạy gần nhất ({run.get('run_date', 'N/A')}):\n{run.get('summary', 'Không có tóm tắt')}")
        
        # Open investigations
        investigations = context.get("open_investigations", [])
        if investigations:
            inv_lines = []
            for inv in investigations:
                priority_icon = "⚡" if inv.get('priority') == 'high' else "📋"
                title = inv.get('source_event_title') or 'N/A'
                question = inv.get('question') or inv.get('item', 'N/A')
                inv_lines.append(f"- {priority_icon} [{inv['id']}] {question}")
                inv_lines.append(f"  (nguồn: {title[:50]}...)" if len(title) > 50 else f"  (nguồn: {title})")
            sections.append(f"### Các điểm cần điều tra (OPEN - {len(investigations)} items):\n" + "\n".join(inv_lines))
        
        # Recurring topics
        topics = context.get("recurring_topics", [])
        if topics:
            topic_text = "\n".join([
                f"- {'🔥' if t.get('is_hot') else '📊'} {t['topic']}: xuất hiện {t['occurrence_count']} lần"
                for t in topics
            ])
            sections.append(f"### Chủ đề xuất hiện nhiều lần (Hot Topics):\n{topic_text}")
        
        # Pending predictions
        predictions = context.get("recent_predictions", [])
        if predictions:
            pred_text = "\n".join([
                f"- [{p['check_by_date']}] {p['prediction']} (confidence: {p['confidence']})"
                for p in predictions
            ])
            sections.append(f"### Dự đoán cần kiểm tra:\n{pred_text}")
        
        # Key events
        events = context.get("key_events_last_period", [])
        if events:
            event_text = "\n".join([
                f"- [{e.get('published_at', 'N/A')}] {e['title']} (score: {e.get('current_score', e.get('base_score', 'N/A'))})"
                for e in events[:10]
            ])
            sections.append(f"### Sự kiện quan trọng gần đây:\n{event_text}")
        
        # Indicator trends
        indicators = context.get("indicator_trends", [])
        if indicators:
            ind_text = []
            for ind in indicators:
                trend_icon = "↑" if ind.get('trend') == 'up' else ("↓" if ind.get('trend') == 'down' else "→")
                change_str = f" ({ind['change']:+.2f})" if ind.get('change') else ""
                ind_text.append(f"- {ind['name']}: {ind['value']} {ind.get('unit', '')}{change_str} {trend_icon}")
            sections.append(f"### Xu hướng chỉ số:\n" + "\n".join(ind_text[:15]))
        
        return "\n\n".join(sections) if sections else "Không có context từ các lần chạy trước."
