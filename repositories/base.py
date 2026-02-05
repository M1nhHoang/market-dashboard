"""
Base Repository Pattern with SQLAlchemy

Provides common async CRUD operations for all repositories.
"""
from datetime import datetime, date
from typing import TypeVar, Generic, Optional, List, Sequence, Type, Any
import uuid

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.base import Base


# Generic type for model classes
ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Base repository with common async database operations.
    
    Subclasses should set the `model` class attribute to their specific
    SQLAlchemy model class.
    
    Example:
        class IndicatorRepository(BaseRepository[Indicator]):
            model = Indicator
    """
    
    model: Type[ModelT]
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    # ============================================
    # READ OPERATIONS
    # ============================================
    
    async def get(self, entity_id: str) -> Optional[ModelT]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Primary key value
            
        Returns:
            Entity or None if not found
        """
        return await self.session.get(self.model, entity_id)
    
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "id",
        descending: bool = False
    ) -> Sequence[ModelT]:
        """
        Get all entities with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Column name to sort by
            descending: Sort in descending order
            
        Returns:
            List of entities
        """
        column = getattr(self.model, order_by)
        if descending:
            column = column.desc()
        
        stmt = select(self.model).order_by(column).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_ids(self, entity_ids: List[str]) -> Sequence[ModelT]:
        """
        Get multiple entities by their IDs.
        
        Args:
            entity_ids: List of primary key values
            
        Returns:
            List of found entities
        """
        if not entity_ids:
            return []
        
        stmt = select(self.model).where(self.model.id.in_(entity_ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def count(self) -> int:
        """
        Count all entities.
        
        Returns:
            Total count
        """
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()
    
    async def exists(self, entity_id: str) -> bool:
        """
        Check if entity exists.
        
        Args:
            entity_id: Primary key value
            
        Returns:
            True if exists, False otherwise
        """
        stmt = select(func.count()).select_from(self.model).where(
            self.model.id == entity_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0
    
    # ============================================
    # WRITE OPERATIONS
    # ============================================
    
    async def add(self, entity: ModelT) -> ModelT:
        """
        Add a new entity.
        
        Args:
            entity: Entity to add
            
        Returns:
            Added entity with any auto-generated values
        """
        self.session.add(entity)
        await self.session.flush()
        return entity
    
    async def add_all(self, entities: List[ModelT]) -> List[ModelT]:
        """
        Add multiple entities.
        
        Args:
            entities: List of entities to add
            
        Returns:
            List of added entities
        """
        self.session.add_all(entities)
        await self.session.flush()
        return entities
    
    async def update(self, entity: ModelT) -> ModelT:
        """
        Update an existing entity.
        
        Args:
            entity: Entity with updated values
            
        Returns:
            Updated entity
        """
        merged = await self.session.merge(entity)
        await self.session.flush()
        return merged
    
    async def delete(self, entity_id: str) -> bool:
        """
        Delete entity by ID.
        
        Args:
            entity_id: Primary key value
            
        Returns:
            True if deleted, False if not found
        """
        entity = await self.get(entity_id)
        if entity:
            await self.session.delete(entity)
            await self.session.flush()
            return True
        return False
    
    async def delete_all(self, entity_ids: List[str]) -> int:
        """
        Delete multiple entities by IDs.
        
        Args:
            entity_ids: List of primary key values
            
        Returns:
            Number of deleted entities
        """
        if not entity_ids:
            return 0
        
        stmt = delete(self.model).where(self.model.id.in_(entity_ids))
        result = await self.session.execute(stmt)
        return result.rowcount
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    @staticmethod
    def generate_id(prefix: str = "") -> str:
        """
        Generate unique ID with optional prefix.
        
        Args:
            prefix: Optional prefix for the ID
            
        Returns:
            Unique ID string
        """
        unique_part = uuid.uuid4().hex[:12]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        base_id = f"{timestamp}_{unique_part}"
        return f"{prefix}_{base_id}" if prefix else base_id
    
    @staticmethod
    def now() -> datetime:
        """Get current datetime."""
        return datetime.now()
    
    @staticmethod
    def today() -> date:
        """Get current date."""
        return date.today()
