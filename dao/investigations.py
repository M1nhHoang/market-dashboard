"""
Investigation Repository

Handles all database operations for investigations and evidence.
"""
from typing import Optional, List, Dict, Any

from loguru import logger

from .base import BaseRepository
from .entities import Investigation, InvestigationEvidence, Prediction


class InvestigationRepository(BaseRepository[Investigation]):
    """Repository for investigation operations."""
    
    TABLE_NAME = "investigations"
    
    def _row_to_entity(self, row: Any) -> Investigation:
        """Convert database row to Investigation entity."""
        return Investigation(
            id=row["id"],
            question=row["question"],
            context=row["context"],
            source_event_id=row["source_event_id"],
            status=row["status"],
            priority=row["priority"],
            evidence_count=row["evidence_count"] or 0,
            evidence_summary=row["evidence_summary"],
            resolution=row["resolution"],
            resolution_confidence=row["resolution_confidence"],
            resolved_by_event_id=row["resolved_by_event_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_evidence_at=row["last_evidence_at"],
            resolved_at=row["resolved_at"],
            related_indicators=self._json_decode(row["related_indicators"]) or [],
            related_templates=self._json_decode(row["related_templates"]) or [],
            source_event_title=row.get("source_event_title"),
        )
    
    # ============================================
    # INVESTIGATION CRUD
    # ============================================
    
    def create(
        self,
        question: str,
        source_event_id: str,
        priority: str = "medium",
        context: str = None,
        related_indicators: List[str] = None,
        related_templates: List[str] = None,
    ) -> str:
        """
        Create a new investigation.
        
        Args:
            question: Investigation question
            source_event_id: Event that triggered this investigation
            priority: Priority level (high/medium/low)
            context: Additional context
            related_indicators: List of related indicator IDs
            related_templates: List of related template IDs
            
        Returns:
            Investigation ID
        """
        inv_id = self._generate_id("inv")
        now = self._now()
        
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO investigations (
                    id, question, context, source_event_id, status, priority,
                    evidence_count, related_indicators, related_templates,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'open', ?, 0, ?, ?, ?, ?)
            """, (
                inv_id, question, context, source_event_id, priority,
                self._json_encode(related_indicators or []),
                self._json_encode(related_templates or []),
                now, now
            ))
        
        logger.info(f"Created investigation: {inv_id} - {question[:50]}...")
        return inv_id
    
    def update_status(
        self,
        investigation_id: str,
        status: str = None,
        evidence_summary: str = None,
        resolution: str = None,
        resolution_confidence: str = None,
        resolved_by_event_id: str = None,
    ) -> bool:
        """
        Update investigation status.
        
        Args:
            investigation_id: Investigation ID
            status: New status
            evidence_summary: Updated evidence summary
            resolution: Resolution text
            resolution_confidence: Confidence in resolution
            resolved_by_event_id: Event that resolved this
            
        Returns:
            True if updated
        """
        updates = {"updated_at": self._now()}
        
        if status:
            updates["status"] = status
        if evidence_summary:
            updates["evidence_summary"] = evidence_summary
        if resolution:
            updates["resolution"] = resolution
        if resolution_confidence:
            updates["resolution_confidence"] = resolution_confidence
        if resolved_by_event_id:
            updates["resolved_by_event_id"] = resolved_by_event_id
        if status == 'resolved':
            updates["resolved_at"] = self._now()
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        params = list(updates.values()) + [investigation_id]
        
        with self.db.transaction() as conn:
            cursor = conn.execute(
                f"UPDATE investigations SET {set_clause} WHERE id = ?",
                params
            )
            return cursor.rowcount > 0
    
    # ============================================
    # QUERY METHODS
    # ============================================
    
    def get_open(self) -> List[Investigation]:
        """Get all open investigations with source event info."""
        cursor = self.db.execute("""
            SELECT i.*, e.title as source_event_title
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
        return [self._row_to_entity(row) for row in cursor.fetchall()]
    
    def get_by_status(self, status: str) -> List[Investigation]:
        """Get investigations by status."""
        return self.find_where("status = ?", (status,), order_by="created_at DESC")
    
    def get_by_priority(self, priority: str) -> List[Investigation]:
        """Get investigations by priority."""
        return self.find_where(
            "priority = ? AND status IN ('open', 'updated')",
            (priority,),
            order_by="created_at DESC"
        )
    
    def get_stale(self, days: int = 14) -> List[Investigation]:
        """Get investigations with no updates in N days."""
        cursor = self.db.execute("""
            SELECT * FROM investigations 
            WHERE status IN ('open', 'updated')
            AND updated_at < datetime('now', ?)
            ORDER BY updated_at ASC
        """, (f'-{days} days',))
        return [self._row_to_entity(row) for row in cursor.fetchall()]
    
    # ============================================
    # EVIDENCE
    # ============================================
    
    def add_evidence(
        self,
        investigation_id: str,
        event_id: str,
        evidence_type: str,
        summary: str
    ) -> str:
        """
        Add evidence to an investigation.
        
        Args:
            investigation_id: Investigation ID
            event_id: Event providing evidence
            evidence_type: Type (supports/contradicts/neutral)
            summary: Evidence summary
            
        Returns:
            Evidence ID
        """
        evidence_id = self._generate_id("evd")
        now = self._now()
        
        with self.db.transaction() as conn:
            # Insert evidence
            conn.execute("""
                INSERT INTO investigation_evidence (
                    id, investigation_id, event_id, evidence_type, summary, added_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (evidence_id, investigation_id, event_id, evidence_type, summary, now))
            
            # Update investigation
            conn.execute("""
                UPDATE investigations 
                SET evidence_count = evidence_count + 1,
                    last_evidence_at = ?,
                    status = CASE WHEN status = 'open' THEN 'updated' ELSE status END,
                    updated_at = ?
                WHERE id = ?
            """, (now, now, investigation_id))
        
        logger.debug(f"Added evidence to investigation {investigation_id}: {evidence_type}")
        return evidence_id
    
    def get_evidence(self, investigation_id: str) -> List[InvestigationEvidence]:
        """Get all evidence for an investigation."""
        cursor = self.db.execute("""
            SELECT * FROM investigation_evidence 
            WHERE investigation_id = ?
            ORDER BY added_at DESC
        """, (investigation_id,))
        
        return [InvestigationEvidence(
            id=row["id"],
            investigation_id=row["investigation_id"],
            event_id=row["event_id"],
            evidence_type=row["evidence_type"],
            summary=row["summary"],
            added_at=row["added_at"],
        ) for row in cursor.fetchall()]
    
    def get_evidence_summary(self, investigation_id: str) -> Dict[str, Any]:
        """Get summary of evidence for an investigation."""
        evidence = self.get_evidence(investigation_id)
        
        return {
            "total": len(evidence),
            "supports": len([e for e in evidence if e.evidence_type == "supports"]),
            "contradicts": len([e for e in evidence if e.evidence_type == "contradicts"]),
            "neutral": len([e for e in evidence if e.evidence_type == "neutral"]),
            "evidence": [e.__dict__ for e in evidence[:5]],  # Latest 5
        }
    
    # ============================================
    # PREDICTIONS
    # ============================================
    
    def create_prediction(self, prediction: Dict[str, Any]) -> str:
        """Create a prediction."""
        pred_id = self._generate_id("pred")
        
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO predictions (
                    id, prediction, based_on_events, source_event_id,
                    confidence, check_by_date, verification_indicator,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (
                pred_id,
                prediction.get('prediction'),
                self._json_encode(prediction.get('based_on_events', [])),
                prediction.get('source_event_id'),
                prediction.get('confidence'),
                prediction.get('check_by_date'),
                prediction.get('verification_indicator'),
                self._now(),
            ))
        
        logger.info(f"Created prediction: {pred_id}")
        return pred_id
    
    def get_pending_predictions(self) -> List[Prediction]:
        """Get predictions that need to be checked."""
        cursor = self.db.execute("""
            SELECT * FROM predictions 
            WHERE status = 'pending'
            AND check_by_date <= date('now')
            ORDER BY check_by_date ASC
        """)
        
        return [Prediction(
            id=row["id"],
            prediction=row["prediction"],
            based_on_events=self._json_decode(row["based_on_events"]) or [],
            source_event_id=row["source_event_id"],
            confidence=row["confidence"],
            check_by_date=row["check_by_date"],
            verification_indicator=row["verification_indicator"],
            status=row["status"],
            actual_outcome=row["actual_outcome"],
            verified_at=row["verified_at"],
            created_at=row["created_at"],
        ) for row in cursor.fetchall()]
    
    def update_prediction(
        self,
        prediction_id: str,
        status: str,
        actual_outcome: str = None
    ) -> bool:
        """Update prediction status."""
        with self.db.transaction() as conn:
            cursor = conn.execute("""
                UPDATE predictions SET
                    status = ?,
                    actual_outcome = ?,
                    verified_at = ?
                WHERE id = ?
            """, (status, actual_outcome, self._now(), prediction_id))
            return cursor.rowcount > 0
