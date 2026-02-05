"""
Unified Data Models for Crawler Output

These dataclasses define the standard structure that all crawlers
must produce after transformation. This enables:
- Unified pipeline processing
- Type safety
- Easy extension for new data sources
"""

from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Optional, Dict, List, Any
from enum import Enum


class MetricType(str, Enum):
    """Types of metrics that can be collected."""
    EXCHANGE_RATE = "exchange_rate"
    INTERBANK_RATE = "interbank_rate"
    POLICY_RATE = "policy_rate"
    GOLD_PRICE = "gold_price"
    CPI = "cpi"
    OMO = "omo"
    CREDIT = "credit"
    # Future types
    INDEX = "index"
    BOND_YIELD = "bond_yield"
    COMMODITY = "commodity"


class EventType(str, Enum):
    """Types of events/news."""
    NEWS = "news"
    PRESS_RELEASE = "press_release"
    CIRCULAR = "circular"
    ANNOUNCEMENT = "announcement"
    LEGAL_DOCUMENT = "legal_document"


@dataclass
class MetricRecord:
    """
    A single metric data point (time-series).
    
    This represents any numeric value that changes over time
    and needs to be tracked in indicator/indicator_history tables.
    
    Examples:
        - Exchange rate: USD/VND = 25067
        - Interbank ON rate: 9.12%
        - OMO net injection: 80926 tỷ VND
        - CPI MoM: 0.19%
    """
    # Identity
    metric_type: MetricType          # Category of metric
    metric_id: str                   # Unique ID (e.g., "interbank_on", "usd_vnd_central")
    
    # Value
    value: float                     # The numeric value
    unit: str                        # Unit of measurement (%, VND, tỷ VND, etc.)
    
    # Time
    date: date                       # Date of the value
    period: Optional[str] = None     # For periodic data: "2025-12" (monthly), "2025-Q4" (quarterly)
    
    # Metadata
    name: Optional[str] = None       # Display name (English)
    name_vi: Optional[str] = None    # Display name (Vietnamese)
    
    # Additional attributes (flexible, metric-specific)
    attributes: Dict[str, Any] = field(default_factory=dict)
    # Examples:
    # - interbank: {"volume": 902773.0, "term": "Qua đêm"}
    # - gold: {"buy_price": 177200000, "sell_price": 179000000, "organization": "SJC"}
    # - omo: {"inject": 80926, "withdraw": 0, "by_term": {"7d": 40731, "28d": 24582}}
    # - cpi: {"month": 12, "year": 2025, "yoy_change": 3.38, "core_inflation": 3.19}
    
    # Source
    source: str = ""                 # Data source (SBV, Yahoo, Fed, etc.)
    source_url: Optional[str] = None
    
    def __post_init__(self):
        """Convert string metric_type to enum if needed."""
        if isinstance(self.metric_type, str):
            self.metric_type = MetricType(self.metric_type)


@dataclass
class EventRecord:
    """
    A news/event item that needs LLM analysis.
    
    Events flow through the LLM pipeline for:
    - Classification (is_market_relevant, category)
    - Scoring (base_score, score_factors)
    - Causal analysis (template matching)
    """
    # Identity
    event_type: EventType            # Type of event
    
    # Content
    title: str                       # Event title
    summary: Optional[str] = None    # Brief summary
    content: Optional[str] = None    # Full content (if available)
    
    # Time
    published_at: Optional[datetime] = None
    
    # Source
    source: str = ""
    source_url: Optional[str] = None
    
    # Metadata
    language: str = "vi"             # Content language
    categories: List[str] = field(default_factory=list)  # Source categories/tags
    
    # Processing hints
    has_full_content: bool = False   # True if content was successfully fetched
    
    # Attachments
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    # Format: [{"url": "...", "type": "pdf", "title": "..."}]
    
    def __post_init__(self):
        """Convert string event_type to enum if needed."""
        if isinstance(self.event_type, str):
            self.event_type = EventType(self.event_type)


@dataclass
class CalendarRecord:
    """
    A future scheduled economic event.
    
    Calendar events are saved directly to calendar_events table
    without LLM processing.
    """
    # Identity
    event_name: str                  # Event name (e.g., "US CPI", "FOMC Meeting")
    country: str                     # Country code (VN, US, CN, EU, JP, etc.)
    
    # Time
    date: date                       # Event date
    time: Optional[time] = None      # Event time (if known)
    
    # Importance
    importance: str = "medium"       # high, medium, low
    
    # Values
    previous: Optional[str] = None   # Previous value
    forecast: Optional[str] = None   # Forecasted value
    actual: Optional[str] = None     # Actual value (filled after event)
    
    # Source
    source: str = ""
    source_url: Optional[str] = None


@dataclass
class CrawlerOutput:
    """
    Universal output structure for all crawlers.
    
    After a crawler fetches data, it's transformed into this structure.
    This enables:
    - Unified pipeline processing
    - Consistent database operations
    - Easy extension for new sources
    
    Flow:
        Crawler.fetch() → raw_data → Transformer.transform() → CrawlerOutput
    """
    # Metadata
    source: str                      # Crawler source name (sbv, yahoo, investing, etc.)
    crawled_at: datetime             # When the crawl happened
    success: bool                    # Overall success status
    error: Optional[str] = None      # Error message if any
    
    # Statistics (source-specific)
    stats: Dict[str, Any] = field(default_factory=dict)
    # Example:
    # {
    #     "total_items": 60,
    #     "exchange_rates_count": 1,
    #     "interbank_rates_count": 7,
    #     "news_count": 20,
    #     "errors": []
    # }
    
    # The 3 core data types
    metrics: List[MetricRecord] = field(default_factory=list)
    events: List[EventRecord] = field(default_factory=list)
    calendar: List[CalendarRecord] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source,
            "crawled_at": self.crawled_at.isoformat(),
            "success": self.success,
            "error": self.error,
            "stats": self.stats,
            "metrics": [self._metric_to_dict(m) for m in self.metrics],
            "events": [self._event_to_dict(e) for e in self.events],
            "calendar": [self._calendar_to_dict(c) for c in self.calendar],
        }
    
    def _metric_to_dict(self, m: MetricRecord) -> Dict[str, Any]:
        return {
            "metric_type": m.metric_type.value if isinstance(m.metric_type, MetricType) else m.metric_type,
            "metric_id": m.metric_id,
            "value": m.value,
            "unit": m.unit,
            "date": m.date.isoformat() if isinstance(m.date, date) else m.date,
            "period": m.period,
            "name": m.name,
            "name_vi": m.name_vi,
            "attributes": m.attributes,
            "source": m.source,
            "source_url": m.source_url,
        }
    
    def _event_to_dict(self, e: EventRecord) -> Dict[str, Any]:
        return {
            "event_type": e.event_type.value if isinstance(e.event_type, EventType) else e.event_type,
            "title": e.title,
            "summary": e.summary,
            "content": e.content,
            "published_at": e.published_at.isoformat() if e.published_at else None,
            "source": e.source,
            "source_url": e.source_url,
            "language": e.language,
            "categories": e.categories,
            "has_full_content": e.has_full_content,
            "attachments": e.attachments,
        }
    
    def _calendar_to_dict(self, c: CalendarRecord) -> Dict[str, Any]:
        return {
            "event_name": c.event_name,
            "country": c.country,
            "date": c.date.isoformat() if isinstance(c.date, date) else c.date,
            "time": c.time.isoformat() if c.time else None,
            "importance": c.importance,
            "previous": c.previous,
            "forecast": c.forecast,
            "actual": c.actual,
            "source": c.source,
            "source_url": c.source_url,
        }
    
    @property
    def metrics_count(self) -> int:
        return len(self.metrics)
    
    @property
    def events_count(self) -> int:
        return len(self.events)
    
    @property
    def calendar_count(self) -> int:
        return len(self.calendar)
    
    def summary(self) -> str:
        """Return a brief summary of the output."""
        return (
            f"CrawlerOutput(source={self.source}, "
            f"metrics={self.metrics_count}, "
            f"events={self.events_count}, "
            f"calendar={self.calendar_count}, "
            f"success={self.success})"
        )
