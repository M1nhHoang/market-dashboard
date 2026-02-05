# Data Flow Documentation

## Overview

Hệ thống xử lý dữ liệu theo pipeline hourly với 5 bước chính:
1. **Crawl** - Thu thập dữ liệu từ nhiều nguồn (raw output)
2. **Transform** - Chuyển đổi raw data → unified structure
3. **Process** - Xử lý events qua 3 layers LLM
4. **Store** - Lưu vào database
5. **Serve** - Cung cấp qua API cho frontend

---

## Data Taxonomy

Tất cả dữ liệu được phân thành **3 categories chính**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA TAXONOMY                                     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│      METRICS        │  │       EVENTS        │  │      CALENDAR       │
│   (Time Series)     │  │   (Occurrences)     │  │  (Future Schedule)  │
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│ • Có VALUE số       │  │ • Có CONTENT text   │  │ • Có DATE tương lai │
│ • Có HISTORY        │  │ • One-time          │  │ • Có FORECAST       │
│ • Cần TRACK trend   │  │ • Cần ANALYZE (LLM) │  │ • Cần REMIND        │
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│ Examples:           │  │ Examples:           │  │ Examples:           │
│ - Exchange rate     │  │ - SBV news          │  │ - FOMC meeting      │
│ - Interbank rates   │  │ - Press releases    │  │ - VN CPI release    │
│ - Policy rates      │  │ - Announcements     │  │ - Fed decision      │
│ - Gold price        │  │ - Circulars         │  │ - GDP report        │
│ - CPI               │  │                     │  │                     │
│ - OMO volumes       │  │                     │  │                     │
│ - Fed rate (future) │  │                     │  │                     │
│ - DXY (future)      │  │                     │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
   ┌───────────┐           ┌───────────┐           ┌───────────┐
   │indicators │           │  events   │           │ calendar  │
   │  (table)  │           │  (table)  │           │  (table)  │
   └───────────┘           └───────────┘           └───────────┘
```

---

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HOURLY PIPELINE                                  │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────┐
    │                        DATA SOURCES                              │
    │                                                                  │
    │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐   │
    │   │   SBV   │  │  News   │  │Calendar │  │     Global      │   │
    │   │ Crawler │  │ Crawler │  │ Crawler │  │    Crawler      │   │
    │   └────┬────┘  └────┬────┘  └────┬────┘  └────────┬────────┘   │
    │        │            │            │                │            │
    │        └────────────┴────────────┴────────────────┘            │
    │                             │                                   │
    └─────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                     RAW DATA (per source)                        │
    │                                                                  │
    │   sbv_raw.json, yahoo_raw.json, investing_raw.json, ...         │
    │   → Saved to: data/raw/{source}_{date}.json                     │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                     TRANSFORM LAYER                              │
    │                                                                  │
    │   Raw Data ──▶ Transformer (per source) ──▶ CrawlerOutput       │
    │                                                                  │
    │   CrawlerOutput {                                                │
    │     source: "sbv",                                               │
    │     metrics: [...],    # → indicators table                     │
    │     events: [...],     # → LLM pipeline → events table          │
    │     calendar: [...]    # → calendar_events table                │
    │   }                                                              │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    LLM PROCESSING PIPELINE                       │
    │                    (Only for EVENTS)                             │
    │                                                                  │
    │   ┌─────────────────────────────────────────────────────────┐   │
    │   │              LAYER 1: CLASSIFICATION                     │   │
    │   │                                                          │   │
    │   │   Input: Raw news articles                               │   │
    │   │   Output:                                                │   │
    │   │     - is_market_relevant: boolean                        │   │
    │   │     - category: monetary|fiscal|banking|...              │   │
    │   │     - linked_indicators: [indicator_ids]                 │   │
    │   │                                                          │   │
    │   │   Filter: Only relevant news → Layer 2                   │   │
    │   └─────────────────────────┬───────────────────────────────┘   │
    │                             │                                    │
    │                             ▼                                    │
    │   ┌─────────────────────────────────────────────────────────┐   │
    │   │              LAYER 2: SCORING & ANALYSIS                 │   │
    │   │                                                          │   │
    │   │   Input: Classified news + Context (30 days)             │   │
    │   │   Context includes:                                      │   │
    │   │     - Open investigations                                │   │
    │   │     - Recent predictions                                 │   │
    │   │     - Hot topics                                         │   │
    │   │     - Indicator trends                                   │   │
    │   │                                                          │   │
    │   │   Output:                                                │   │
    │   │     - base_score: 1-100                                  │   │
    │   │     - score_factors breakdown                            │   │
    │   │     - causal_analysis (matched template)                 │   │
    │   │     - investigation_action (resolve/create)              │   │
    │   │     - predictions                                        │   │
    │   └─────────────────────────┬───────────────────────────────┘   │
    │                             │                                    │
    │                             ▼                                    │
    │   ┌─────────────────────────────────────────────────────────┐   │
    │   │              LAYER 3: RANKING & DECAY                    │   │
    │   │                                                          │   │
    │   │   Input: ALL active events (not just today)              │   │
    │   │                                                          │   │
    │   │   Process:                                               │   │
    │   │     1. Apply time decay (day 0: 100% → day 30: 30%)     │   │
    │   │     2. Apply boost factors:                              │   │
    │   │        - Follow-up to investigation: +20%                │   │
    │   │        - Part of hot topic: +15%                         │   │
    │   │        - Multi-indicator link: +10%                      │   │
    │   │     3. Assign display_section                            │   │
    │   │     4. Identify hot topics (3+ in 7 days)               │   │
    │   │                                                          │   │
    │   │   Output:                                                │   │
    │   │     - current_score                                      │   │
    │   │     - display_section                                    │   │
    │   │     - hot_topic badge                                    │   │
    │   └─────────────────────────────────────────────────────────┘   │
    │                                                                  │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                        DATABASE                                  │
    │                                                                  │
    │   ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐   │
    │   │   indicators    │  │     events      │  │investigations │   │
    │   │   (current)     │  │ (analyzed news) │  │  (questions)  │   │
    │   └────────┬────────┘  └────────┬────────┘  └───────┬───────┘   │
    │            │                    │                   │           │
    │   ┌────────┴────────┐  ┌───────┴────────┐  ┌───────┴───────┐   │
    │   │indicator_history│  │causal_analyses │  │   evidence    │   │
    │   │   (timeline)    │  │ (chains)       │  │  (timeline)   │   │
    │   └─────────────────┘  └────────────────┘  └───────────────┘   │
    │                                                                  │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                       FASTAPI SERVER                             │
    │                                                                  │
    │   /api/indicators      → Dashboard indicators panel             │
    │   /api/events/key      → Key events list                        │
    │   /api/events/other    → Other news (collapsed)                 │
    │   /api/investigations  → Investigation panel                    │
    │   /api/calendar        → Economic calendar                      │
    │                                                                  │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                      REACT DASHBOARD                             │
    │                                                                  │
    │   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
    │   │  Indicators  │  │  Key Events  │  │   Investigations     │  │
    │   │    Panel     │  │    List      │  │      Panel           │  │
    │   └──────────────┘  └──────────────┘  └──────────────────────┘  │
    │                                                                  │
    └─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Step-by-Step Flow

### Step 1: Crawler Execution

```python
# scheduler.py - runs every hour
@scheduler.scheduled_job('cron', hour='*')
def hourly_job():
    run_pipeline()
```

**Raw Crawler Output** (source-specific, flat structure):
```python
# Actual SBV raw output structure
{
    "source": "sbv",
    "crawled_at": "2026-02-04T11:40:24",
    "success": True,
    "data": [
        # Flat array with 'type' field to distinguish
        {"type": "exchange_rate", "name": "USD/VND Central Rate", "value": 25067.0, ...},
        {"type": "gold_price", "name": "Giá vàng SJC", "buy_price": 177200000.0, ...},
        {"type": "policy_rate", "name": "Lãi suất tái chiết khấu", "value": 3.0, ...},
        {"type": "interbank_rate", "term": "Qua đêm", "avg_rate": 9.12, "volume": 902773.0, ...},
        {"type": "cpi", "month": 12, "year": 2025, "mom_change": 0.19, ...},
        {"type": "omo", "transaction_type": "Mua kỳ hạn", "term": "7 ngày", "volume": 35983.63, ...},
        {"type": "news", "title": "Hội nghị...", "summary": "...", "content": "...", ...}
    ],
    "count": 62
}
```

---

### Step 2: Transform Layer

**Purpose:** Convert raw source-specific data → unified `CrawlerOutput` structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRANSFORM LAYER                                  │
└─────────────────────────────────────────────────────────────────────────┘

   Raw Crawler Output              Transformer                Unified Output
   (source-specific)               (per source)               (standard)
         │                              │                          │
         ▼                              ▼                          ▼
┌─────────────────┐           ┌─────────────────┐        ┌─────────────────┐
│ sbv_raw.json    │──────────▶│ SBVTransformer  │───────▶│                 │
│ {               │           │                 │        │ CrawlerOutput   │
│   data: [...]   │           │ - map types     │        │ {               │
│ }               │           │ - aggregate OMO │        │   metrics: [...] │
└─────────────────┘           │ - extract news  │        │   events: [...]  │
                              └─────────────────┘        │   calendar: []   │
                                                         │ }               │
┌─────────────────┐           ┌─────────────────┐        │                 │
│ yahoo_raw.json  │──────────▶│ YahooTransformer│───────▶│                 │
└─────────────────┘           └─────────────────┘        │                 │
                                                         │                 │
┌─────────────────┐           ┌─────────────────┐        │                 │
│ investing_raw   │──────────▶│CalendarTransform│───────▶│                 │
└─────────────────┘           └─────────────────┘        └─────────────────┘
```

**Unified CrawlerOutput Structure:**
```python
@dataclass
class CrawlerOutput:
    """Universal structure for all crawlers"""
    
    # Metadata
    source: str                    # "sbv", "investing", "yahoo"
    crawled_at: datetime
    success: bool
    error: Optional[str]
    stats: Dict[str, Any]          # Source-specific stats
    
    # The 3 core data types
    metrics: List[MetricRecord]    # Time series → indicators table
    events: List[EventRecord]      # News → LLM pipeline → events table
    calendar: List[CalendarRecord] # Schedule → calendar_events table


@dataclass
class MetricRecord:
    """Any numeric time-series data point"""
    
    metric_type: str       # "exchange_rate", "interbank_rate", "omo", "cpi", "gold_price"
    metric_id: str         # "usd_vnd_central", "interbank_on", "omo_inject"
    value: float
    unit: str              # "VND", "%", "tỷ VND"
    date: date
    period: Optional[str]  # "2025-12" for monthly, None for daily
    attributes: Dict       # volume, term, buy_price, etc.
    source: str
    source_url: Optional[str]


@dataclass  
class EventRecord:
    """News, announcements, press releases"""
    
    event_type: str        # "news", "press_release", "circular"
    title: str
    summary: Optional[str]
    content: Optional[str]
    published_at: datetime
    source: str
    source_url: Optional[str]
    language: str          # "vi", "en"


@dataclass
class CalendarRecord:
    """Future scheduled economic events"""
    
    event_name: str
    country: str           # "VN", "US", "CN"
    date: date
    time: Optional[time]
    importance: str        # "high", "medium", "low"
    previous: Optional[str]
    forecast: Optional[str]
    actual: Optional[str]
    source: str
```

**SBV Transform Example:**
```python
class SBVTransformer:
    def transform(self, raw_data: dict) -> CrawlerOutput:
        metrics = []
        events = []
        
        for item in raw_data["data"]:
            if item["type"] == "exchange_rate":
                metrics.append(MetricRecord(
                    metric_type="exchange_rate",
                    metric_id="usd_vnd_central",
                    value=item["value"],
                    unit="VND",
                    date=parse_date(item["date"]),
                    attributes={},
                    source="SBV"
                ))
            
            elif item["type"] == "interbank_rate":
                metrics.append(MetricRecord(
                    metric_type="interbank_rate",
                    metric_id=INTERBANK_TERM_MAP[item["term"]],  # "interbank_on"
                    value=item["avg_rate"],
                    unit="%",
                    date=parse_date(item["date"]),
                    attributes={"volume": item["volume"]},
                    source="SBV"
                ))
            
            elif item["type"] == "omo":
                # Aggregate by date, only use is_total=True rows
                ...
            
            elif item["type"] == "news":
                events.append(EventRecord(
                    event_type="news",
                    title=item["title"],
                    summary=item.get("summary"),
                    content=item.get("content"),
                    published_at=parse_datetime(item["date"]),
                    source="SBV",
                    source_url=item["source_url"],
                    language="vi"
                ))
        
        return CrawlerOutput(
            source="sbv",
            crawled_at=parse_datetime(raw_data["crawled_at"]),
            success=raw_data["success"],
            error=raw_data.get("error"),
            stats=raw_data["data"][0]["stats"] if raw_data["data"] else {},
            metrics=metrics,
            events=events,
            calendar=[]
        )
```

**Metric Type Mapping:**
| Raw `type` | `metric_type` | `metric_id` |
|------------|---------------|-------------|
| `exchange_rate` | `exchange_rate` | `usd_vnd_central` |
| `interbank_rate` (Qua đêm) | `interbank_rate` | `interbank_on` |
| `interbank_rate` (1 Tuần) | `interbank_rate` | `interbank_1w` |
| `interbank_rate` (2 Tuần) | `interbank_rate` | `interbank_2w` |
| `interbank_rate` (1 Tháng) | `interbank_rate` | `interbank_1m` |
| `policy_rate` (tái chiết khấu) | `policy_rate` | `rediscount_rate` |
| `policy_rate` (tái cấp vốn) | `policy_rate` | `refinancing_rate` |
| `gold_price` (SJC) | `gold_price` | `gold_sjc` |
| `cpi` | `cpi` | `cpi_mom` |
| `omo` (aggregated) | `omo` | `omo_inject`, `omo_withdraw`, `omo_net` |

---

### Step 3: Layer 1 - Classification

**Input:** EventRecord from transform layer
**Output:** Classification result

```python
# For each event
classification = llm.generate(CLASSIFICATION_PROMPT.format(
    article=event.content or event.summary
))

# Output
{
    "is_market_relevant": True,
    "category": "monetary",
    "linked_indicators": ["interbank_on", "omo_net_daily"],
    "reasoning": "OMO operation directly affects interbank liquidity"
}
```

**Decision:**
- `is_market_relevant = True` → Continue to Layer 2
- `is_market_relevant = False` → Skip, don't save

---

### Step 4: Layer 2 - Scoring & Analysis

**Input:** 
- Classified news
- Previous context (30 days)

**Context Building:**
```python
context = {
    "open_investigations": [
        {
            "id": "inv_001",
            "question": "Will deposit rates increase?",
            "evidence_count": 3,
            "status": "updated"
        }
    ],
    "hot_topics": [
        {"topic": "interbank liquidity", "count": 5}
    ],
    "recent_predictions": [...],
    "indicator_trends": {
        "interbank_on": {"trend": "up", "7d_change": "+0.5%"}
    }
}
```

**Output:**
```python
{
    "base_score": 85,
    "score_factors": {
        "direct_indicator_impact": 28,  # /30
        "policy_significance": 22,       # /25
        "market_breadth": 18,            # /20
        "novelty": 10,                   # /15
        "source_authority": 7            # /10
    },
    
    "causal_analysis": {
        "matched_template_id": "omo_injection",
        "chain": [
            {"step": 1, "event": "SBV net injects via OMO", "status": "verified"},
            {"step": 2, "event": "Banking liquidity improves", "status": "likely"},
            {"step": 3, "event": "Short-term rates stabilize", "status": "uncertain"}
        ],
        "confidence": "likely"
    },
    
    "investigation_action": {
        "resolves": null,
        "creates_new": True,
        "new_investigation": {
            "question": "Will ON rate decrease tomorrow?",
            "priority": "medium"
        }
    },
    
    "predictions": [
        {
            "prediction": "ON rate may decrease to 8.5-9.0%",
            "confidence": "medium",
            "check_by_date": "2026-02-07"
        }
    ]
}
```

---

### Step 5: Layer 3 - Ranking

**Input:** ALL active events (past 30 days)

**Time Decay Formula:**
```python
def calculate_decay(age_days: int) -> float:
    if age_days == 0:
        return 1.0
    elif age_days <= 3:
        return 0.9
    elif age_days <= 7:
        return 0.7
    elif age_days <= 14:
        return 0.5
    elif age_days <= 30:
        return 0.3
    else:
        return 0  # Archive
```

**Boost Factors:**
```python
boost = 1.0
if is_follow_up_to_investigation:
    boost += 0.20
if is_hot_topic:
    boost += 0.15
if len(linked_indicators) >= 2:
    boost += 0.10
```

**Final Score:**
```python
current_score = base_score * decay_factor * boost_factor
```

**Display Section Assignment:**
```python
if current_score >= 50 and linked_indicators:
    display_section = "key_events"
elif is_market_relevant and current_score >= 20:
    display_section = "other_news"
else:
    display_section = "archive"
```

---

### Step 6: Database Storage

**Parallel Paths:**
```
CrawlerOutput
     │
     ├─── metrics ──────────────▶ indicators + indicator_history
     │                           (direct save, no LLM)
     │
     ├─── events ───▶ LLM ──────▶ events + causal_analyses + investigations
     │               Pipeline    (processed through 3 layers)
     │
     └─── calendar ─────────────▶ calendar_events
                                  (direct save, no LLM)
```

**Metrics Save Sequence:**
1. Upsert `indicators` with latest values
2. Insert into `indicator_history` if value changed from previous

**Events Save Sequence:**
1. Insert new `events` (with LLM analysis)
2. Insert `causal_analyses` for each event
3. Create/update `investigations`
4. Add `investigation_evidence`
5. Record `predictions`
6. Update `topic_frequency`

**Calendar Save Sequence:**
1. Upsert `calendar_events` (UNIQUE on date + event_name + country)

**Run History:**
```python
run_history = RunHistory(
    run_date=today,
    raw_data_path="data/raw/sbv_2026-02-05.json",
    sources_crawled=["sbv"],
    crawl_stats={
        "sbv": {"metrics": 25, "events": 20, "calendar": 0}
    },
    events_extracted=5,
    events_key=2,
    events_other=3,
    status="success"
)
```

**Deduplication:**
```python
# Events deduplicated by hash
hash = hashlib.md5(f"{title}{source}{content[:200]}".encode()).hexdigest()

# Check if exists
existing = await session.execute(
    select(Event).where(Event.hash == hash)
)
if existing.scalar():
    return  # Skip duplicate
```

---

### Step 7: API Serving

**Key Endpoints Flow:**

```
GET /api/indicators
    ↓
    Query: SELECT * FROM indicators ORDER BY category
    ↓
    Response: Grouped by category for panel display

GET /api/events/key
    ↓
    Query: SELECT * FROM events 
           WHERE display_section = 'key_events'
           ORDER BY current_score DESC
           LIMIT 15
    ↓
    Include: causal_analyses, linked indicators

GET /api/investigations
    ↓
    Query: SELECT * FROM investigations
           WHERE status IN ('open', 'updated')
           ORDER BY priority, updated_at DESC
    ↓
    Include: evidence timeline
```

---

## Investigation Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INVESTIGATION LIFECYCLE                               │
└─────────────────────────────────────────────────────────────────────────┘

   Event Analysis           New Event              New Event
   (Layer 2)                (Layer 2)              (Layer 2)
        │                        │                      │
        │ creates                │ provides             │ provides
        │ new question           │ evidence             │ evidence
        ▼                        ▼                      ▼
   ┌─────────┐             ┌──────────┐           ┌──────────┐
   │  OPEN   │────────────▶│ UPDATED  │──────────▶│ RESOLVED │
   └─────────┘   evidence  └──────────┘   answer  └──────────┘
        │        added          │         found
        │                       │
        │ no update             │ conflicting
        │ > 14 days             │ evidence
        ▼                       ▼
   ┌─────────┐             ┌──────────┐
   │  STALE  │             │ESCALATED │
   └─────────┘             └──────────┘
        │                       │
        │ auto-close            │ human review
        ▼                       ▼
   ┌─────────┐             ┌──────────┐
   │ CLOSED  │             │ RESOLVED │
   └─────────┘             └──────────┘
                           (manual)
```

---

## Context Continuity

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      30-DAY CONTEXT WINDOW                               │
└─────────────────────────────────────────────────────────────────────────┘

   Day -30        Day -7         Day -1          Today
      │             │              │               │
      ▼             ▼              ▼               ▼
   ┌──────┐     ┌──────┐       ┌──────┐       ┌──────┐
   │Events│     │Events│       │Events│       │ New  │
   │ old  │     │recent│       │latest│       │Events│
   └──────┘     └──────┘       └──────┘       └──────┘
      │             │              │               │
      └─────────────┴──────────────┴───────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   CONTEXT SUMMARY   │
              │                     │
              │ - Open questions    │
              │ - Hot topics        │
              │ - Recurring themes  │
              │ - Indicator trends  │
              │ - Pending predictions│
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   LLM LAYER 2       │
              │   (with context)    │
              │                     │
              │ Enables:            │
              │ - Link to past      │
              │ - Resolve questions │
              │ - Detect patterns   │
              │ - Avoid redundancy  │
              └─────────────────────┘
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       ERROR HANDLING                                     │
└─────────────────────────────────────────────────────────────────────────┘

   ┌─────────────┐
   │   Crawler   │──────▶ Fails ──────▶ Log error, continue with other sources
   │   (Step 1)  │                      Set run_history.status = 'partial'
   └─────────────┘

   ┌─────────────┐
   │ Transformer │──────▶ Fails ──────▶ Log error, skip this source
   │  (Step 2)   │                      Continue with other sources
   └─────────────┘

   ┌─────────────┐
   │    LLM      │──────▶ Fails ──────▶ Retry once with exponential backoff
   │ (Step 3-5)  │                      If still fails: save raw for manual review
   └─────────────┘

   ┌─────────────┐
   │  Database   │──────▶ Fails ──────▶ CRITICAL - stop pipeline, alert
   │  (Step 6)   │                      Rollback transaction
   └─────────────┘

   ┌─────────────┐
   │   Context   │──────▶ Fails ──────▶ Run with empty context, log warning
   │   Build     │                      Continue processing
   └─────────────┘
```

---

## File Storage

```
data/
├── raw/
│   ├── sbv_2026-02-05.json       # Raw SBV crawler output
│   ├── yahoo_2026-02-05.json     # Raw Yahoo crawler output (future)
│   └── investing_2026-02-05.json # Raw Investing crawler output (future)
│
├── processed/
│   └── 2026-02-05/
│       ├── transformed.json      # After transform layer
│       ├── classified.json       # Layer 1 output
│       ├── scored.json           # Layer 2 output
│       └── ranked.json           # Layer 3 output
│
└── context/
    └── context_summary.json      # Cached context for LLM
```

**run_history tracks:**
```python
{
    "raw_data_path": "data/raw/sbv_2026-02-05.json",
    "sources_crawled": ["sbv"],
    "crawl_stats": {
        "sbv": {
            "metrics": 25,   # exchange_rate, interbank, policy, gold, cpi, omo
            "events": 20,    # news items
            "calendar": 0,
            "errors": 0
        }
    }
}
```

---

## Extensibility Guide

### Adding a New Data Source

**Step 1: Create Crawler**
```python
# crawlers/yahoo_crawler.py
class YahooCrawler(BaseCrawler):
    def crawl(self) -> dict:
        # Return raw data in any structure
        return {
            "source": "yahoo",
            "crawled_at": datetime.now().isoformat(),
            "data": [...],  # Source-specific structure
            "success": True
        }
```

**Step 2: Create Transformer**
```python
# processor/transformers/yahoo_transformer.py
class YahooTransformer(BaseTransformer):
    def transform(self, raw_data: dict) -> CrawlerOutput:
        metrics = []
        
        for item in raw_data["data"]:
            metrics.append(MetricRecord(
                metric_type="index",
                metric_id="dxy",
                value=item["close"],
                unit="",
                date=parse_date(item["date"]),
                attributes={"open": item["open"], "high": item["high"], "low": item["low"]},
                source="Yahoo Finance"
            ))
        
        return CrawlerOutput(
            source="yahoo",
            metrics=metrics,
            events=[],
            calendar=[]
        )
```

**Step 3: Register in Pipeline**
```python
# processor/pipeline.py
CRAWLERS = {
    "sbv": SBVCrawler,
    "yahoo": YahooCrawler,      # Add new crawler
}

TRANSFORMERS = {
    "sbv": SBVTransformer,
    "yahoo": YahooTransformer,  # Add new transformer
}
```

### Adding a New Metric Type

**Step 1: Define metric_id mapping**
```python
# constants/indicator_mappings.py
INDICATOR_GROUPS = {
    "global_macro": {
        "display_name": "🌍 Global",
        "indicators": [
            "dxy",          # New metric
            "us10y",        # New metric
            "fed_rate",     # New metric
        ]
    }
}
```

**Step 2: Add to transformer**
```python
# In transformer, map source data to metric_id
if item["symbol"] == "DX-Y.NYB":
    metric_id = "dxy"
elif item["symbol"] == "^TNX":
    metric_id = "us10y"
```

### Adding Calendar Data

```python
# Any crawler can return calendar data
class InvestingTransformer(BaseTransformer):
    def transform(self, raw_data: dict) -> CrawlerOutput:
        calendar = []
        
        for event in raw_data["economic_calendar"]:
            calendar.append(CalendarRecord(
                event_name=event["name"],
                country=event["country"],
                date=parse_date(event["date"]),
                time=parse_time(event["time"]) if event.get("time") else None,
                importance=event["importance"],
                previous=event.get("previous"),
                forecast=event.get("forecast"),
                source="Investing.com"
            ))
        
        return CrawlerOutput(
            source="investing",
            metrics=[],
            events=[],
            calendar=calendar  # Calendar data
        )
```

### Summary: Extension Points

| To Add... | Create/Modify |
|-----------|---------------|
| New data source | 1. Crawler, 2. Transformer, 3. Register in pipeline |
| New metric type | 1. Add to INDICATOR_GROUPS, 2. Add mapping in transformer |
| New event type | 1. Add `event_type` in EventRecord |
| New calendar source | 1. Return CalendarRecord in transformer |
