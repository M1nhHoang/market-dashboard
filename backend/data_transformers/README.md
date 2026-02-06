# Data Transformers Module

Transforms raw crawler output to unified `CrawlerOutput` structure.

## Architecture

```
data_transformers/
├── models.py                    # Shared models (CrawlerOutput, MetricRecord...)
├── base.py                      # BaseTransformer (abstract)
│
└── sbv/                         # SBV source
    ├── __init__.py
    ├── transformer.py           # SBVTransformer
    └── mappings.py              # SBV-specific mappings

constants/
└── enums.py                     # Shared enums (DisplaySection, PriorityLevel, etc.)
```

## Usage

```python
from data_transformers import SBVTransformer, CrawlerOutput

# Load raw data from crawler
raw_data = sbv_crawler.fetch()

# Transform to unified structure
transformer = SBVTransformer()
output: CrawlerOutput = transformer.transform(raw_data)

# Access data
print(f"Metrics: {output.metrics_count}")
print(f"Events: {output.events_count}")
print(f"Calendar: {output.calendar_count}")

# Iterate metrics by type
for metric in output.metrics:
    if metric.metric_type == MetricType.INTERBANK_RATE:
        print(f"{metric.metric_id}: {metric.value}%")
```

## Accessing SBV Mappings

```python
# For SBV-specific mappings, import from sbv submodule
from data_transformers.sbv import (
    INTERBANK_TERM_MAP,
    POLICY_RATE_MAP,
    GOLD_PRICE_MAP,
    INDICATOR_GROUPS,
    INDICATOR_DEFAULTS,
    EVENT_CATEGORIES,
)
```

## Data Models

### MetricRecord
Time-series numeric data (exchange rates, interest rates, CPI, OMO, etc.)

```python
@dataclass
class MetricRecord:
    metric_type: MetricType      # EXCHANGE_RATE, INTERBANK_RATE, OMO, CPI, etc.
    metric_id: str               # "usd_vnd_central", "interbank_on", etc.
    value: float                 # The numeric value
    unit: str                    # "VND", "%", "tỷ VND", etc.
    date: date                   # Date of the value
    period: Optional[str]        # For monthly data: "2025-12"
    name: Optional[str]          # Display name (English)
    name_vi: Optional[str]       # Display name (Vietnamese)
    attributes: Dict[str, Any]   # Additional data (volume, term, etc.)
    source: str
    source_url: Optional[str]
```

### EventRecord
News/events that need LLM analysis.

```python
@dataclass
class EventRecord:
    event_type: EventType        # NEWS, PRESS_RELEASE, CIRCULAR, etc.
    title: str
    summary: Optional[str]
    content: Optional[str]
    published_at: Optional[datetime]
    source: str
    source_url: Optional[str]
    language: str                # "vi", "en"
    categories: List[str]
    has_full_content: bool
    attachments: List[Dict]
```

### CalendarRecord
Future scheduled economic events.

```python
@dataclass
class CalendarRecord:
    event_name: str
    country: str                 # "VN", "US", "CN", etc.
    date: date
    time: Optional[time]
    importance: str              # "high", "medium", "low"
    previous: Optional[str]
    forecast: Optional[str]
    actual: Optional[str]
    source: str
```

## Adding New Transformers

1. Create new file: `data_transformers/{source}_transformer.py`
2. Inherit from `BaseTransformer`
3. Implement `transform()` method

```python
from data_transformers.base import BaseTransformer
from data_transformers.models import CrawlerOutput, MetricRecord, EventRecord

class NewSourceTransformer(BaseTransformer):
    @property
    def source_name(self) -> str:
        return "new_source"
    
    def transform(self, raw_data: dict) -> CrawlerOutput:
        metrics = []
        events = []
        calendar = []
        
        # Transform logic here...
        
        return CrawlerOutput(
            source=self.source_name,
            crawled_at=datetime.now(),
            success=True,
            metrics=metrics,
            events=events,
            calendar=calendar,
        )
```

4. Export in `__init__.py`:
```python
from .new_source_transformer import NewSourceTransformer
```

## Metric Type Mapping (SBV)

| Raw `type` | MetricType | `metric_id` |
|------------|------------|-------------|
| `exchange_rate` | `EXCHANGE_RATE` | `usd_vnd_central` |
| `interbank_rate` (Qua đêm) | `INTERBANK_RATE` | `interbank_on` |
| `interbank_rate` (1 Tuần) | `INTERBANK_RATE` | `interbank_1w` |
| `policy_rate` (tái chiết khấu) | `POLICY_RATE` | `rediscount_rate` |
| `policy_rate` (tái cấp vốn) | `POLICY_RATE` | `refinancing_rate` |
| `gold_price` (SJC) | `GOLD_PRICE` | `gold_sjc` |
| `cpi` (mom) | `CPI` | `cpi_mom` |
| `cpi` (yoy) | `CPI` | `cpi_yoy` |
| `cpi` (ytd) | `CPI` | `cpi_ytd` |
| `cpi` (core) | `CPI` | `core_inflation` |
| `omo` (aggregated) | `OMO` | `omo_net_daily`, `omo_inject_daily`, `omo_withdraw_daily` |
| `news` | (EventRecord) | N/A |

## SBV OMO Aggregation

Raw OMO data comes as multiple records per day. Transformer aggregates:

```python
# Input: Multiple OMO records per day
{"type": "omo", "transaction_type": "Mua kỳ hạn", "term": "7 ngày", "volume": 35983.63}
{"type": "omo", "transaction_type": "Mua kỳ hạn", "term": "Tổng cộng", "volume": 35983.63, "is_total": True}
{"type": "omo", "transaction_type": "Mua kỳ hạn", "term": "28 ngày", "volume": 19182.93}
# ... more records

# Output: Aggregated metrics
MetricRecord(metric_id="omo_net_daily", value=80926.88, attributes={
    "inject": 80926.88,
    "withdraw": 0,
    "by_term": {"7d": 40731.40, "28d": 24581.58, "56d": 15613.90}
})
```
