"""
Base Repository Pattern

Provides common CRUD operations and query building utilities.
All specific repositories inherit from this base class.
"""
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Any, TypeVar, Generic, Dict, List
from dataclasses import dataclass, asdict

from loguru import logger


T = TypeVar('T')


@dataclass
class Entity:
    """
    Base entity class with common fields.
    
    Note: All fields have defaults to allow subclass flexibility.
    ID should always be provided when creating entities.
    """
    id: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """Create entity from dictionary."""
        return cls(**data)


class BaseRepository(ABC, Generic[T]):
    """
    Base repository with common database operations.
    
    Subclasses must implement:
    - TABLE_NAME: str
    - _row_to_entity(): Convert database row to entity
    """
    
    TABLE_NAME: str = ""
    
    def __init__(self, db: "DatabaseConnection"):
        """
        Initialize repository with database connection.
        
        Args:
            db: DatabaseConnection instance
        """
        self.db = db
    
    # ============================================
    # ABSTRACT METHODS
    # ============================================
    
    @abstractmethod
    def _row_to_entity(self, row: Any) -> T:
        """Convert a database row to entity object."""
        pass
    
    # ============================================
    # COMMON CRUD OPERATIONS
    # ============================================
    
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Primary key value
            
        Returns:
            Entity or None if not found
        """
        cursor = self.db.execute(
            f"SELECT * FROM {self.TABLE_NAME} WHERE id = ?",
            (entity_id,)
        )
        row = cursor.fetchone()
        return self._row_to_entity(row) if row else None
    
    def get_all(
        self, 
        limit: int = 100, 
        offset: int = 0,
        order_by: str = "id"
    ) -> List[T]:
        """
        Get all entities with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Column to sort by
            
        Returns:
            List of entities
        """
        cursor = self.db.execute(
            f"SELECT * FROM {self.TABLE_NAME} ORDER BY {order_by} LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return [self._row_to_entity(row) for row in cursor.fetchall()]
    
    def count(self, where: str = None, params: tuple = ()) -> int:
        """
        Count entities.
        
        Args:
            where: Optional WHERE clause
            params: Query parameters
            
        Returns:
            Count of entities
        """
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME}"
        if where:
            query += f" WHERE {where}"
        
        cursor = self.db.execute(query, params)
        return cursor.fetchone()[0]
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        cursor = self.db.execute(
            f"SELECT 1 FROM {self.TABLE_NAME} WHERE id = ? LIMIT 1",
            (entity_id,)
        )
        return cursor.fetchone() is not None
    
    def delete(self, entity_id: str) -> bool:
        """
        Delete entity by ID.
        
        Args:
            entity_id: Primary key value
            
        Returns:
            True if deleted, False if not found
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                f"DELETE FROM {self.TABLE_NAME} WHERE id = ?",
                (entity_id,)
            )
            return cursor.rowcount > 0
    
    # ============================================
    # QUERY BUILDERS
    # ============================================
    
    def find_where(
        self,
        where: str,
        params: tuple = (),
        order_by: str = None,
        limit: int = None
    ) -> List[T]:
        """
        Find entities matching WHERE clause.
        
        Args:
            where: WHERE clause (without 'WHERE' keyword)
            params: Query parameters
            order_by: Optional ORDER BY clause
            limit: Optional LIMIT
            
        Returns:
            List of matching entities
        """
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE {where}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.db.execute(query, params)
        return [self._row_to_entity(row) for row in cursor.fetchall()]
    
    def find_one_where(self, where: str, params: tuple = ()) -> Optional[T]:
        """Find single entity matching WHERE clause."""
        results = self.find_where(where, params, limit=1)
        return results[0] if results else None
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    @staticmethod
    def _now() -> str:
        """Get current timestamp as ISO string."""
        return datetime.now().isoformat()
    
    @staticmethod
    def _today() -> str:
        """Get current date as string."""
        return datetime.now().strftime('%Y-%m-%d')
    
    @staticmethod
    def _json_encode(data: Any) -> str:
        """Encode data as JSON string."""
        return json.dumps(data, ensure_ascii=False)
    
    @staticmethod
    def _json_decode(data: str) -> Any:
        """Decode JSON string."""
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    
    def _generate_id(self, prefix: str = "") -> str:
        """Generate unique ID with optional prefix."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        return f"{prefix}_{timestamp}" if prefix else timestamp
