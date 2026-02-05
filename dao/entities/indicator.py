"""
Indicator entities.
"""
from dataclasses import dataclass
from typing import Optional

from .base import Entity


@dataclass
class Indicator(Entity):
    """Indicator entity representing current indicator values."""
    name: str = ""
    value: Optional[float] = None
    name_vi: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    unit: Optional[str] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    trend: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class IndicatorHistory(Entity):
    """Indicator history entity for trend analysis."""
    indicator_id: str = ""
    value: float = 0.0
    date: str = ""
    previous_value: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    recorded_at: Optional[str] = None
    source: Optional[str] = None
