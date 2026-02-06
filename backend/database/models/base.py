"""
SQLAlchemy Base Model and Mixins

Provides base classes and common mixins for all models.
"""
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    Provides:
    - Automatic table name from class name
    - Common utility methods
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def __repr__(self) -> str:
        """String representation."""
        class_name = self.__class__.__name__
        pk = getattr(self, 'id', None)
        return f"<{class_name}(id={pk})>"


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamps.
    
    Usage:
        class MyModel(Base, TimestampMixin):
            ...
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=True
    )
