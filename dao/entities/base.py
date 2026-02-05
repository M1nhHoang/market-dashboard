"""
Base Entity class.
"""
from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict


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
