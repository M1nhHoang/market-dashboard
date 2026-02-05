"""
Indicator Repository

Handles all database operations for indicators and indicator history.
"""
from typing import Optional, List, Dict, Any

from loguru import logger

from .base import BaseRepository
from .entities import Indicator, IndicatorHistory


class IndicatorRepository(BaseRepository[Indicator]):
    """Repository for indicator operations."""
    
    TABLE_NAME = "indicators"
    
    def _row_to_entity(self, row: Any) -> Indicator:
        """Convert database row to Indicator entity."""
        return Indicator(
            id=row["id"],
            name=row["name"],
            name_vi=row["name_vi"],
            category=row["category"],
            subcategory=row["subcategory"],
            value=row["value"],
            unit=row["unit"],
            change=row["change"],
            change_pct=row["change_pct"],
            trend=row["trend"],
            source=row["source"],
            source_url=row["source_url"],
            updated_at=row["updated_at"],
        )
    
    def _row_to_history(self, row: Any) -> IndicatorHistory:
        """Convert database row to IndicatorHistory entity."""
        return IndicatorHistory(
            id=row["id"],
            indicator_id=row["indicator_id"],
            value=row["value"],
            previous_value=row["previous_value"],
            change=row["change"],
            change_pct=row["change_pct"],
            volume=row["volume"],
            date=row["date"],
            recorded_at=row["recorded_at"],
            source=row["source"],
        )
    
    # ============================================
    # INDICATOR CRUD
    # ============================================
    
    def get(self, indicator_id: str) -> Optional[Indicator]:
        """Get indicator by ID."""
        return self.get_by_id(indicator_id)
    
    def get_by_category(self, category: str) -> List[Indicator]:
        """Get all indicators in a category."""
        return self.find_where("category = ?", (category,))
    
    def upsert(
        self,
        indicator_id: str,
        name: str,
        value: float,
        unit: str,
        category: str,
        source: str,
        name_vi: str = None,
        subcategory: str = None,
        source_url: str = None,
        change: float = None,
        change_pct: float = None,
        trend: str = None,
    ) -> Indicator:
        """
        Insert or update an indicator.
        
        Args:
            indicator_id: Unique indicator identifier
            name: Display name (English)
            value: Current value
            unit: Unit of measurement
            category: Category for grouping
            source: Data source
            name_vi: Vietnamese display name
            subcategory: Subcategory for further grouping
            source_url: URL to data source
            change: Absolute change from previous value
            change_pct: Percentage change
            trend: Trend direction ('up', 'down', 'stable')
            
        Returns:
            Updated Indicator entity
        """
        now = self._now()
        
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO indicators (
                    id, name, name_vi, category, subcategory, value, unit,
                    change, change_pct, trend, source, source_url, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    value = excluded.value,
                    change = excluded.change,
                    change_pct = excluded.change_pct,
                    trend = excluded.trend,
                    source = excluded.source,
                    source_url = excluded.source_url,
                    updated_at = excluded.updated_at
            """, (
                indicator_id, name, name_vi, category, subcategory, value, unit,
                change, change_pct, trend, source, source_url, now
            ))
        
        return Indicator(
            id=indicator_id,
            name=name,
            name_vi=name_vi,
            category=category,
            subcategory=subcategory,
            value=value,
            unit=unit,
            change=change,
            change_pct=change_pct,
            trend=trend,
            source=source,
            source_url=source_url,
            updated_at=now,
        )
    
    def update_value(
        self,
        indicator_id: str,
        value: float,
        change: float = None,
        change_pct: float = None,
        trend: str = None,
    ) -> bool:
        """
        Update only the value and change fields of an indicator.
        
        Args:
            indicator_id: Indicator to update
            value: New value
            change: Absolute change
            change_pct: Percentage change
            trend: Trend direction
            
        Returns:
            True if updated, False if not found
        """
        with self.db.transaction() as conn:
            cursor = conn.execute("""
                UPDATE indicators SET
                    value = ?,
                    change = ?,
                    change_pct = ?,
                    trend = ?,
                    updated_at = ?
                WHERE id = ?
            """, (value, change, change_pct, trend, self._now(), indicator_id))
            return cursor.rowcount > 0
    
    # ============================================
    # INDICATOR HISTORY
    # ============================================
    
    def save_history(
        self,
        indicator_id: str,
        value: float,
        date: str,
        source: str,
        volume: float = None,
        previous_value: float = None,
    ) -> Optional[str]:
        """
        Save indicator value to history if changed.
        
        Args:
            indicator_id: Indicator ID
            value: Value to save
            date: Date of the value
            source: Data source
            volume: Transaction volume (for interbank)
            previous_value: Previous value for change calculation
            
        Returns:
            History ID if saved, None if duplicate
        """
        # Check for duplicate
        cursor = self.db.execute("""
            SELECT value FROM indicator_history 
            WHERE indicator_id = ? AND date = ?
            ORDER BY recorded_at DESC LIMIT 1
        """, (indicator_id, date))
        row = cursor.fetchone()
        
        if row and row['value'] == value:
            return None  # No change
        
        # Calculate change
        change = None
        change_pct = None
        if previous_value is not None and previous_value != 0:
            change = value - previous_value
            change_pct = (change / previous_value) * 100
        
        history_id = self._generate_id(f"{indicator_id}_{date}")
        
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO indicator_history (
                    id, indicator_id, value, previous_value, change, change_pct,
                    volume, date, recorded_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                history_id, indicator_id, value, previous_value, change, change_pct,
                volume, date, self._now(), source
            ))
        
        logger.debug(f"Saved history: {indicator_id} = {value} on {date}")
        return history_id
    
    def get_history(
        self,
        indicator_id: str,
        days: int = 30,
        start_date: str = None,
        end_date: str = None,
    ) -> List[IndicatorHistory]:
        """
        Get indicator history.
        
        Args:
            indicator_id: Indicator ID
            days: Number of days to look back (ignored if start_date provided)
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of history entries, most recent first
        """
        if start_date and end_date:
            cursor = self.db.execute("""
                SELECT * FROM indicator_history 
                WHERE indicator_id = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (indicator_id, start_date, end_date))
        else:
            cursor = self.db.execute("""
                SELECT * FROM indicator_history 
                WHERE indicator_id = ? 
                ORDER BY date DESC 
                LIMIT ?
            """, (indicator_id, days))
        
        return [self._row_to_history(row) for row in cursor.fetchall()]
    
    def get_latest_history(self, indicator_id: str) -> Optional[IndicatorHistory]:
        """Get most recent history entry for an indicator."""
        cursor = self.db.execute("""
            SELECT * FROM indicator_history 
            WHERE indicator_id = ? 
            ORDER BY date DESC, recorded_at DESC
            LIMIT 1
        """, (indicator_id,))
        row = cursor.fetchone()
        return self._row_to_history(row) if row else None
    
    def get_trend(self, indicator_id: str, periods: int = 5) -> Dict[str, Any]:
        """
        Calculate trend for an indicator.
        
        Args:
            indicator_id: Indicator ID
            periods: Number of periods to analyze
            
        Returns:
            Dict with trend analysis
        """
        history = self.get_history(indicator_id, days=periods)
        
        if len(history) < 2:
            return {"direction": "unknown", "strength": 0, "data_points": len(history)}
        
        values = [h.value for h in history]
        changes = [values[i] - values[i+1] for i in range(len(values)-1)]
        
        # Determine direction
        avg_change = sum(changes) / len(changes)
        if avg_change > 0:
            direction = "up"
        elif avg_change < 0:
            direction = "down"
        else:
            direction = "stable"
        
        # Calculate strength (0-100)
        if values[0] != 0:
            total_change_pct = abs((values[0] - values[-1]) / values[-1] * 100)
        else:
            total_change_pct = 0
        
        return {
            "direction": direction,
            "avg_change": avg_change,
            "total_change_pct": total_change_pct,
            "data_points": len(history),
            "latest_value": values[0] if values else None,
            "oldest_value": values[-1] if values else None,
        }
    
    # ============================================
    # BULK OPERATIONS
    # ============================================
    
    def bulk_upsert(self, indicators: List[Dict[str, Any]]) -> int:
        """
        Bulk upsert multiple indicators.
        
        Args:
            indicators: List of indicator dicts with id, name, value, etc.
            
        Returns:
            Number of indicators processed
        """
        count = 0
        for ind in indicators:
            self.upsert(
                indicator_id=ind["id"],
                name=ind["name"],
                value=ind.get("value"),
                unit=ind.get("unit", ""),
                category=ind.get("category", ""),
                source=ind.get("source", ""),
                name_vi=ind.get("name_vi"),
                subcategory=ind.get("subcategory"),
                source_url=ind.get("source_url"),
                change=ind.get("change"),
                change_pct=ind.get("change_pct"),
                trend=ind.get("trend"),
            )
            count += 1
        return count
    
    def get_all_with_trends(self) -> List[Dict[str, Any]]:
        """Get all indicators with trend information."""
        indicators = self.get_all()
        result = []
        
        for ind in indicators:
            ind_dict = ind.to_dict()
            trend_info = self.get_trend(ind.id, periods=5)
            ind_dict["trend_info"] = trend_info
            result.append(ind_dict)
        
        return result
