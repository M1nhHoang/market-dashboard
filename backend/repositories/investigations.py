"""
Investigation Repository

Handles all database operations for investigations, evidence, and predictions.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Sequence

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Investigation, InvestigationEvidence, Prediction
from .base import BaseRepository


class InvestigationRepository(BaseRepository[Investigation]):
    """Repository for investigation operations."""
    
    model = Investigation
    
    # ============================================
    # INVESTIGATION QUERIES
    # ============================================
    
    async def get_with_evidence(
        self,
        investigation_id: str
    ) -> Optional[Investigation]:
        """Get investigation with all evidence loaded."""
        stmt = (
            select(Investigation)
            .options(selectinload(Investigation.evidence))
            .where(Investigation.id == investigation_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_open(self, limit: int = 50) -> Sequence[Investigation]:
        """Get all open investigations."""
        stmt = (
            select(Investigation)
            .where(Investigation.status == "open")
            .order_by(
                # Priority order: high, medium, low
                Investigation.priority.desc(),
                desc(Investigation.created_at)
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: str,
        limit: int = 50
    ) -> Sequence[Investigation]:
        """Get investigations by status."""
        stmt = (
            select(Investigation)
            .where(Investigation.status == status)
            .order_by(desc(Investigation.updated_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_priority(
        self,
        priority: str,
        limit: int = 50
    ) -> Sequence[Investigation]:
        """Get investigations by priority."""
        stmt = (
            select(Investigation)
            .where(
                and_(
                    Investigation.priority == priority,
                    Investigation.status == "open",
                )
            )
            .order_by(desc(Investigation.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_stale(self, days_threshold: int = 14) -> Sequence[Investigation]:
        """
        Get stale investigations (no updates for X days).
        
        Args:
            days_threshold: Number of days without update to consider stale
        """
        cutoff = self.now() - timedelta(days=days_threshold)
        
        stmt = (
            select(Investigation)
            .where(
                and_(
                    Investigation.status == "open",
                    or_(
                        Investigation.updated_at < cutoff,
                        Investigation.updated_at.is_(None),
                    ),
                )
            )
            .order_by(Investigation.created_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_related_to_indicator(
        self,
        indicator_id: str
    ) -> Sequence[Investigation]:
        """Get investigations related to a specific indicator."""
        stmt = (
            select(Investigation)
            .where(Investigation.related_indicators.contains([indicator_id]))
            .order_by(desc(Investigation.created_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    # ============================================
    # INVESTIGATION CREATION & UPDATE
    # ============================================
    
    async def create_investigation(
        self,
        question: str,
        context: str = None,
        source_event_id: str = None,
        priority: str = "medium",
        related_indicators: List[str] = None,
        related_templates: List[str] = None,
    ) -> Investigation:
        """Create a new investigation."""
        now = self.now()
        
        investigation = Investigation(
            id=self.generate_id("inv"),
            question=question,
            context=context,
            source_event_id=source_event_id,
            status="open",
            priority=priority,
            evidence_count=0,
            related_indicators=related_indicators or [],
            related_templates=related_templates or [],
            created_at=now,
            updated_at=now,
        )
        
        return await self.add(investigation)
    
    async def update_status(
        self,
        investigation_id: str,
        status: str,
        resolution: str = None,
        resolution_confidence: str = None,
        resolved_by_event_id: str = None,
    ) -> Optional[Investigation]:
        """Update investigation status."""
        investigation = await self.get(investigation_id)
        if not investigation:
            return None
        
        investigation.status = status
        investigation.updated_at = self.now()
        
        if status == "resolved":
            investigation.resolution = resolution
            investigation.resolution_confidence = resolution_confidence
            investigation.resolved_by_event_id = resolved_by_event_id
            investigation.resolved_at = self.now()
        
        return await self.update(investigation)
    
    async def resolve(
        self,
        investigation_id: str,
        resolution: str,
        confidence: str = "medium",
        resolved_by_event_id: str = None,
    ) -> Optional[Investigation]:
        """Resolve an investigation."""
        return await self.update_status(
            investigation_id=investigation_id,
            status="resolved",
            resolution=resolution,
            resolution_confidence=confidence,
            resolved_by_event_id=resolved_by_event_id,
        )
    
    # ============================================
    # EVIDENCE MANAGEMENT
    # ============================================
    
    async def add_evidence(
        self,
        investigation_id: str,
        event_id: str,
        evidence_type: str,  # 'supports', 'contradicts', 'neutral'
        summary: str,
    ) -> Optional[InvestigationEvidence]:
        """Add evidence to an investigation."""
        investigation = await self.get(investigation_id)
        if not investigation:
            return None
        
        now = self.now()
        
        evidence = InvestigationEvidence(
            id=self.generate_id("ev"),
            investigation_id=investigation_id,
            event_id=event_id,
            evidence_type=evidence_type,
            summary=summary,
            added_at=now,
        )
        
        self.session.add(evidence)
        
        # Update investigation
        investigation.evidence_count = (investigation.evidence_count or 0) + 1
        investigation.last_evidence_at = now
        investigation.updated_at = now
        investigation.status = "updated"
        
        await self.session.flush()
        return evidence
    
    async def get_evidence(
        self,
        investigation_id: str
    ) -> Sequence[InvestigationEvidence]:
        """Get all evidence for an investigation."""
        stmt = (
            select(InvestigationEvidence)
            .where(InvestigationEvidence.investigation_id == investigation_id)
            .order_by(desc(InvestigationEvidence.added_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_evidence_summary(
        self,
        investigation_id: str,
        summary: str,
    ) -> Optional[Investigation]:
        """Update the evidence summary for an investigation."""
        investigation = await self.get(investigation_id)
        if not investigation:
            return None
        
        investigation.evidence_summary = summary
        investigation.updated_at = self.now()
        
        return await self.update(investigation)
    
    # ============================================
    # PREDICTIONS
    # ============================================
    
    async def create_prediction(
        self,
        prediction: str,
        source_event_id: str = None,
        based_on_events: List[str] = None,
        confidence: str = "medium",
        check_by_date: date = None,
        verification_indicator: str = None,
    ) -> Prediction:
        """Create a new prediction."""
        now = self.now()
        
        pred = Prediction(
            id=self.generate_id("pred"),
            prediction=prediction,
            source_event_id=source_event_id,
            based_on_events=based_on_events or [],
            confidence=confidence,
            check_by_date=check_by_date,
            verification_indicator=verification_indicator,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        
        self.session.add(pred)
        await self.session.flush()
        return pred
    
    async def get_pending_predictions(
        self,
        limit: int = 50
    ) -> Sequence[Prediction]:
        """Get all pending predictions."""
        stmt = (
            select(Prediction)
            .where(Prediction.status == "pending")
            .order_by(Prediction.check_by_date)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_due_predictions(self) -> Sequence[Prediction]:
        """Get predictions that are due for verification."""
        today = self.today()
        
        stmt = (
            select(Prediction)
            .where(
                and_(
                    Prediction.status == "pending",
                    Prediction.check_by_date <= today,
                )
            )
            .order_by(Prediction.check_by_date)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def verify_prediction(
        self,
        prediction_id: str,
        status: str,  # 'verified', 'failed', 'expired'
        actual_outcome: str = None,
    ) -> Optional[Prediction]:
        """Update prediction with verification result."""
        stmt = select(Prediction).where(Prediction.id == prediction_id)
        result = await self.session.execute(stmt)
        pred = result.scalar_one_or_none()
        
        if not pred:
            return None
        
        pred.status = status
        pred.actual_outcome = actual_outcome
        pred.verified_at = self.now()
        pred.updated_at = self.now()
        
        await self.session.flush()
        return pred
