"""
LLM Call History Repository

Repository for storing and querying LLM call history.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import LLMCallHistory
from .base import BaseRepository


class LLMHistoryRepository(BaseRepository[LLMCallHistory]):
    """Repository for LLM call history operations."""
    
    model = LLMCallHistory
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
    
    async def get_by_task_type(
        self, 
        task_type: str, 
        limit: int = 100
    ) -> List[LLMCallHistory]:
        """Get calls filtered by task type."""
        query = (
            select(LLMCallHistory)
            .where(LLMCallHistory.task_type == task_type)
            .order_by(LLMCallHistory.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_run_id(self, run_id: str) -> List[LLMCallHistory]:
        """Get all calls from a specific pipeline run."""
        query = (
            select(LLMCallHistory)
            .where(LLMCallHistory.run_id == run_id)
            .order_by(LLMCallHistory.timestamp.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        task_type: Optional[str] = None
    ) -> List[LLMCallHistory]:
        """Get calls within a date range."""
        conditions = [
            LLMCallHistory.timestamp >= start_date,
            LLMCallHistory.timestamp <= end_date
        ]
        if task_type:
            conditions.append(LLMCallHistory.task_type == task_type)
        
        query = (
            select(LLMCallHistory)
            .where(and_(*conditions))
            .order_by(LLMCallHistory.timestamp.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_for_finetuning(
        self,
        task_types: Optional[List[str]] = None,
        min_rating: Optional[int] = None,
        valid_json_only: bool = True,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get calls formatted for fine-tuning export.
        
        Args:
            task_types: Filter by specific task types
            min_rating: Minimum human rating (1-5)
            valid_json_only: Only include calls with valid JSON response
            limit: Maximum number of records
            
        Returns:
            List of dicts in OpenAI fine-tune format
        """
        conditions = []
        
        if task_types:
            conditions.append(LLMCallHistory.task_type.in_(task_types))
        if min_rating is not None:
            conditions.append(LLMCallHistory.human_rating >= min_rating)
        if valid_json_only:
            conditions.append(LLMCallHistory.is_valid_json == True)
        
        query = select(LLMCallHistory).order_by(LLMCallHistory.timestamp.asc())
        
        if conditions:
            query = query.where(and_(*conditions))
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        calls = result.scalars().all()
        
        return [call.to_openai_format() for call in calls]
    
    async def get_statistics(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get usage statistics for the last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Total calls
        total_query = select(func.count(LLMCallHistory.id)).where(
            LLMCallHistory.timestamp >= since
        )
        total_result = await self.session.execute(total_query)
        total_calls = total_result.scalar() or 0
        
        # Total tokens
        tokens_query = select(
            func.sum(LLMCallHistory.input_tokens),
            func.sum(LLMCallHistory.output_tokens),
            func.sum(LLMCallHistory.total_tokens)
        ).where(LLMCallHistory.timestamp >= since)
        tokens_result = await self.session.execute(tokens_query)
        tokens_row = tokens_result.one()
        
        # By task type
        by_task_query = select(
            LLMCallHistory.task_type,
            func.count(LLMCallHistory.id),
            func.sum(LLMCallHistory.total_tokens)
        ).where(
            LLMCallHistory.timestamp >= since
        ).group_by(LLMCallHistory.task_type)
        by_task_result = await self.session.execute(by_task_query)
        by_task = {
            row[0] or "unknown": {"calls": row[1], "tokens": row[2] or 0}
            for row in by_task_result.all()
        }
        
        # Average latency
        latency_query = select(
            func.avg(LLMCallHistory.latency_ms)
        ).where(
            and_(
                LLMCallHistory.timestamp >= since,
                LLMCallHistory.latency_ms.isnot(None)
            )
        )
        latency_result = await self.session.execute(latency_query)
        avg_latency = latency_result.scalar()
        
        return {
            "period_days": days,
            "total_calls": total_calls,
            "total_input_tokens": tokens_row[0] or 0,
            "total_output_tokens": tokens_row[1] or 0,
            "total_tokens": tokens_row[2] or 0,
            "avg_latency_ms": round(avg_latency, 2) if avg_latency else None,
            "by_task_type": by_task
        }
    
    async def cleanup_old_records(self, days: int = 90) -> int:
        """
        Delete records older than N days.
        
        Args:
            days: Delete records older than this many days
            
        Returns:
            Number of records deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Count first
        count_query = select(func.count(LLMCallHistory.id)).where(
            LLMCallHistory.timestamp < cutoff
        )
        count_result = await self.session.execute(count_query)
        count = count_result.scalar() or 0
        
        if count > 0:
            # Delete
            from sqlalchemy import delete
            delete_query = delete(LLMCallHistory).where(
                LLMCallHistory.timestamp < cutoff
            )
            await self.session.execute(delete_query)
            await self.session.commit()
        
        return count
