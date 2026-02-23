"""
Data Transformers Module

Transforms raw crawler output to unified CrawlerOutput structure.
Each crawler has its own transformer submodule.

Usage:
    from data_transformers import SBVTransformer, CrawlerOutput
    
    transformer = SBVTransformer()
    output: CrawlerOutput = transformer.transform(raw_data)

Structure:
    data_transformers/
    ├── models.py           # Shared models (CrawlerOutput, MetricRecord, etc.)
    ├── base.py             # BaseTransformer abstract class
    ├── sbv/                # SBV source
    │   ├── transformer.py  # SBVTransformer
    │   └── mappings.py     # SBV-specific mappings
    ├── vneconomy/          # VnEconomy source
    │   └── transformer.py  # VnEconomyTransformer
    ├── cafef/              # CafeF source
    │   └── transformer.py  # CafeFTransformer
    └── vnexpress/          # VnExpress source
        └── transformer.py  # VnExpressTransformer
"""

from .models import (
    CrawlerOutput,
    MetricRecord,
    EventRecord,
    CalendarRecord,
    MetricType,
    EventType,
)
from .base import BaseTransformer
from .sbv import SBVTransformer
from .vneconomy import VnEconomyTransformer
from .cafef import CafeFTransformer
from .vnexpress import VnExpressTransformer
from .vietcombank import VietcombankTransformer

__all__ = [
    # Models
    "CrawlerOutput",
    "MetricRecord", 
    "EventRecord",
    "CalendarRecord",
    # Enums
    "MetricType",
    "EventType",
    # Transformers
    "BaseTransformer",
    "SBVTransformer",
    "VnEconomyTransformer",
    "CafeFTransformer",
    "VnExpressTransformer",
    "VietcombankTransformer",
]
