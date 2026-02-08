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
    - Active signals (pending predictions)
    - Active themes
    - Recurring topics
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
            "active_signals": self._get_active_signals(),
            "active_themes": self._get_active_themes(),
            "recurring_topics": self._get_recurring_topics(lookback_days),
            "key_events_last_period": self._get_key_events(cutoff_str),
            "indicator_trends": self._get_indicator_trends(lookback_days),
            "context_generated_at": datetime.now().isoformat(),
            "lookback_days": lookback_days
        }
        
        logger.info(f"Built context with {len(context['active_signals'])} active signals, "
                   f"{len(context['active_themes'])} active themes, "
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
    
    def _get_active_signals(self) -> list[dict]:
        """Get all active signals (pending predictions)."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT 
                    s.id,
                    s.prediction,
                    s.direction,
                    s.target_indicator,
                    s.target_range_low,
                    s.target_range_high,
                    s.confidence,
                    s.expires_at,
                    s.created_at,
                    e.title as source_event_title
                FROM signals s
                LEFT JOIN events e ON s.source_event_id = e.id
                WHERE s.status = 'active'
                AND (s.expires_at IS NULL OR s.expires_at > datetime('now'))
                ORDER BY 
                    CASE s.confidence 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        ELSE 3 
                    END,
                    s.created_at DESC
                LIMIT 20
            """)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to get active signals: {e}")
            return []
    
    def _get_active_themes(self) -> list[dict]:
        """Get all active and emerging themes."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT 
                    t.id,
                    t.name,
                    t.name_vi,
                    t.description,
                    t.strength,
                    t.status,
                    t.event_count,
                    t.first_seen,
                    t.last_seen
                FROM themes t
                WHERE t.status IN ('active', 'emerging')
                ORDER BY t.strength DESC, t.event_count DESC
                LIMIT 10
            """)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to get active themes: {e}")
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
        
        # Active signals
        signals = context.get("active_signals", [])
        if signals:
            sig_lines = []
            for sig in signals:
                confidence_icon = "⚡" if sig.get('confidence') == 'high' else "📊"
                direction = sig.get('direction', '?')
                indicator = sig.get('target_indicator', 'unknown')
                sig_lines.append(f"- {confidence_icon} [{sig['id']}] {sig['prediction']}")
                sig_lines.append(f"  (target: {indicator} {direction}, expires: {sig.get('expires_at', 'N/A')})")
            sections.append(f"### Signals đang active ({len(signals)} items):\n" + "\n".join(sig_lines))
        
        # Active themes
        themes = context.get("active_themes", [])
        if themes:
            theme_lines = []
            for theme in themes:
                status_icon = "🔥" if theme.get('status') == 'active' else "📈"
                theme_lines.append(f"- {status_icon} {theme['name']} (strength: {theme.get('strength', 0)}, events: {theme.get('event_count', 0)})")
            sections.append(f"### Themes đang theo dõi ({len(themes)} items):\n" + "\n".join(theme_lines))
        
        # Recurring topics  
        topics = context.get("recurring_topics", [])
        if topics:
            topic_text = "\n".join([
                f"- {'🔥' if t.get('is_hot') else '📊'} {t['topic']}: xuất hiện {t['occurrence_count']} lần"
                for t in topics
            ])
            sections.append(f"### Chủ đề xuất hiện nhiều lần (Hot Topics):\n{topic_text}")
        
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
