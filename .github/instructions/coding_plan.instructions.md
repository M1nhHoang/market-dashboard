---
applyTo: '**'
---
# Market Intelligence Dashboard - Project Instructions

## 1. PROJECT OVERVIEW

Building a Market Intelligence Dashboard that aggregates Vietnam and Global macro/financial news, extracts events, and maps them to predefined causal chains to help the user understand WHY indicators are moving.

### Core Concept
- Input: Raw news + indicator data from various sources
- Processing: Multi-layer LLM analysis with context from previous runs
- Output: Dashboard showing events, indicators, and their causal relationships

### Key Differentiator
Instead of just showing "interest rate went up 0.3%", the system shows:
"Interest rate went up 0.3% BECAUSE: Public investment disbursement increased → KBNN withdrew deposits from banks → Interbank liquidity tightened → Banks raised deposit rates"

### Context Continuity (IMPORTANT)
The LLM processor maintains awareness of previous analyses to:
- Track `needs_investigation` items and resolve them when new evidence appears
- Detect recurring themes (if same topic appears 3+ times → importance signal)
- Link today's events to yesterday's predictions
- Apply time decay to older news for accurate ranking
- Avoid redundant analysis of already-processed information

---

## 2. ARCHITECTURE
```
[Data Sources] → [Crawlers] → [LLM Pipeline] → [SQLite] → [API] → [React Dashboard]
                                    │
                              ┌─────┴─────┐
                              │           │
                         [Layer 1]   [Layer 2]   [Layer 3]
                         Classify    Score       Rank & Decay
                              │           │           │
                              └─────┬─────┘           │
                                    │                 │
                              [Previous Context]──────┘
                              (from 30 days data)
```

### Tech Stack
- **Language**: Python 3.10+
- **Backend**: FastAPI
- **Database**: SQLite (simple, no need for complex DB)
- **LLM**: Claude API (Anthropic)
- **Frontend**: React + Tailwind CSS
- **Scheduler**: Simple cron or APScheduler

### Project Structure
```
market-intelligence/
├── crawlers/
│   ├── __init__.py
│   ├── base_crawler.py       # Abstract base class for crawlers
│   ├── sbv_crawler.py        # Vietnam central bank data (ACTIVE)
│   ├── news_crawler.py       # RSS feeds - TODO: implement later
│   ├── calendar_crawler.py   # Economic calendar - TODO: implement later
│   └── global_crawler.py     # Fed, DXY, commodities - TODO: implement later
├── processor/
│   ├── __init__.py
│   ├── llm_processor.py      # Main LLM orchestrator
│   ├── classifier.py         # Layer 1: Classification
│   ├── scorer.py             # Layer 2: Scoring
│   ├── ranker.py             # Layer 3: Ranking & Decay
│   ├── investigation_reviewer.py  # Investigation status updates
│   ├── context_builder.py    # Builds previous_context for LLM
│   ├── prompts.py            # LLM prompt templates
│   └── output_parser.py      # Parse and validate LLM output
├── templates/
│   └── causal_templates.json # Predefined causal chains (manually curated)
├── api/
│   ├── __init__.py
│   ├── main.py               # FastAPI app
│   └── routes.py             # API endpoints
├── frontend/
│   └── (React app)
├── data/
│   ├── raw/                  # Raw crawled data (JSON files by date)
│   ├── processed/            # LLM output (JSON files by date)
│   ├── context/              # Previous context summaries
│   └── market.db             # SQLite database
├── config.py
├── scheduler.py              # Cron jobs
└── requirements.txt
```

---

## 3. DATA MODELS

### 3.1 SQLite Tables

```sql
-- ============================================
-- INDICATORS
-- ============================================

-- Current indicator values
CREATE TABLE indicators (
    id TEXT PRIMARY KEY,              -- e.g., 'interbank_on', 'usd_vnd_central'
    name TEXT NOT NULL,
    name_vi TEXT,                     -- Vietnamese name
    category TEXT,                    -- 'vietnam_monetary', 'vietnam_forex', etc.
    subcategory TEXT,                 -- For grouping in UI
    value REAL,
    unit TEXT,
    change REAL,
    change_pct REAL,
    trend TEXT,                       -- 'up', 'down', 'stable'
    source TEXT,
    source_url TEXT,
    updated_at TIMESTAMP
);

-- Indicator history for trend analysis
CREATE TABLE indicator_history (
    id TEXT PRIMARY KEY,
    indicator_id TEXT NOT NULL,
    value REAL NOT NULL,
    previous_value REAL,
    change REAL,
    change_pct REAL,
    volume REAL,                      -- For interbank: transaction volume
    date DATE NOT NULL,
    recorded_at TIMESTAMP,
    source TEXT,
    
    UNIQUE(indicator_id, date, value)
);

CREATE INDEX idx_indicator_history_lookup 
ON indicator_history(indicator_id, date DESC);

-- ============================================
-- EVENTS & NEWS
-- ============================================

-- Extracted news events
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    source TEXT,
    source_url TEXT,
    
    -- Classification (Layer 1)
    is_market_relevant BOOLEAN DEFAULT TRUE,
    category TEXT,                    -- 'monetary', 'fiscal', 'banking', etc.
    region TEXT,                      -- 'vietnam', 'global'
    linked_indicators TEXT,           -- JSON array of indicator IDs
    
    -- Scoring (Layer 2)
    base_score INTEGER,               -- 1-100 from LLM
    score_factors TEXT,               -- JSON of scoring breakdown
    
    -- Ranking (Layer 3)
    current_score REAL,               -- After decay & boost
    decay_factor REAL DEFAULT 1.0,
    boost_factor REAL DEFAULT 1.0,
    display_section TEXT,             -- 'key_events', 'other_news', 'archive'
    hot_topic TEXT,                   -- Topic name if part of hot topic
    
    -- Relationships
    is_follow_up BOOLEAN DEFAULT FALSE,
    follows_up_on TEXT,               -- event_id or investigation_id
    
    -- Metadata
    published_at TIMESTAMP,
    created_at TIMESTAMP,
    run_date DATE,
    last_ranked_at TIMESTAMP,
    hash TEXT UNIQUE
);

CREATE INDEX idx_events_display ON events(display_section, current_score DESC);
CREATE INDEX idx_events_date ON events(published_at DESC);

-- ============================================
-- CAUSAL ANALYSIS
-- ============================================

CREATE TABLE causal_analyses (
    id TEXT PRIMARY KEY,
    event_id TEXT REFERENCES events(id),
    template_id TEXT,
    chain_steps TEXT,                 -- JSON array
    confidence TEXT,                  -- 'verified', 'likely', 'uncertain'
    needs_investigation TEXT,         -- JSON array
    affected_indicators TEXT,         -- JSON array
    impact_on_vn TEXT,
    reasoning TEXT,
    created_at TIMESTAMP
);

-- ============================================
-- INVESTIGATIONS
-- ============================================

CREATE TABLE investigations (
    id TEXT PRIMARY KEY,
    
    -- Core info
    question TEXT NOT NULL,
    context TEXT,
    source_event_id TEXT,
    
    -- Status
    status TEXT DEFAULT 'open',       -- 'open', 'updated', 'resolved', 'stale', 'escalated'
    priority TEXT DEFAULT 'medium',   -- 'high', 'medium', 'low'
    
    -- Evidence tracking
    evidence_count INTEGER DEFAULT 0,
    evidence_summary TEXT,
    
    -- Resolution
    resolution TEXT,
    resolution_confidence TEXT,
    resolved_by_event_id TEXT,
    
    -- Timestamps
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_evidence_at TIMESTAMP,
    resolved_at TIMESTAMP,
    
    -- Related
    related_indicators TEXT,          -- JSON array
    related_templates TEXT            -- JSON array
);

CREATE TABLE investigation_evidence (
    id TEXT PRIMARY KEY,
    investigation_id TEXT REFERENCES investigations(id),
    event_id TEXT REFERENCES events(id),
    evidence_type TEXT,               -- 'supports', 'contradicts', 'neutral'
    summary TEXT,
    added_at TIMESTAMP
);

-- ============================================
-- TOPICS & TRENDS
-- ============================================

CREATE TABLE topic_frequency (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    category TEXT,
    occurrence_count INTEGER DEFAULT 1,
    first_seen DATE,
    last_seen DATE,
    related_event_ids TEXT,           -- JSON array
    is_hot BOOLEAN DEFAULT FALSE      -- 3+ occurrences in 7 days
);

-- ============================================
-- SYSTEM
-- ============================================

CREATE TABLE run_history (
    id TEXT PRIMARY KEY,
    run_date DATE,
    run_time TIMESTAMP,
    
    -- Stats
    news_count INTEGER,
    events_extracted INTEGER,
    events_key INTEGER,               -- display_section = 'key_events'
    events_other INTEGER,             -- display_section = 'other_news'
    investigations_opened INTEGER,
    investigations_updated INTEGER,
    investigations_resolved INTEGER,
    
    -- Summary
    summary TEXT,
    status TEXT                       -- 'success', 'partial', 'failed'
);

CREATE TABLE calendar_events (
    id TEXT PRIMARY KEY,
    date DATE,
    time TIME,
    event_name TEXT,
    country TEXT,
    importance TEXT,
    forecast TEXT,
    previous TEXT,
    actual TEXT,
    created_at TIMESTAMP
);

-- ============================================
-- SCORE HISTORY (for analysis)
-- ============================================

CREATE TABLE score_history (
    id TEXT PRIMARY KEY,
    event_id TEXT REFERENCES events(id),
    score REAL,
    decay_factor REAL,
    boost_factor REAL,
    display_section TEXT,
    recorded_at TIMESTAMP
);
```

### 3.2 Indicator Categories & Grouping

```python
INDICATOR_GROUPS = {
    "vietnam_monetary": {
        "display_name": "🏦 Monetary Policy",
        "indicators": [
            "omo_net_daily",
            "rediscount_rate", 
            "refinancing_rate",
            "interbank_on",
            "interbank_1w",
            "interbank_2w",
            "interbank_1m"
        ]
    },
    "vietnam_forex": {
        "display_name": "💱 Exchange Rate",
        "indicators": ["usd_vnd_central"]
    },
    "vietnam_inflation": {
        "display_name": "📈 Inflation",
        "indicators": ["cpi_mom", "cpi_yoy", "core_inflation"]
    },
    "vietnam_commodity": {
        "display_name": "🪙 Commodity",
        "indicators": ["gold_sjc"]
    },
    "global_macro": {
        "display_name": "🌍 Global",
        "indicators": ["fed_rate", "dxy", "us10y", "brent_oil"]
        # TODO: Implement global data sources
    }
}
```

### 3.3 Event Categories

```python
EVENT_CATEGORIES = {
    "monetary": "Monetary policy (OMO, interest rates, liquidity)",
    "fiscal": "Fiscal policy (public investment, budget, tax)",
    "banking": "Banking sector (NPL, credit, bank financials)",
    "economic": "Macroeconomic (GDP, CPI, import/export)",
    "geopolitical": "Geopolitical (trade war, sanctions)",
    "corporate": "Corporate news (non-bank companies)",
    "regulatory": "New regulations, legal changes",
    "internal": "Internal activities (SBV conferences, appointments)"
}
```

### 3.4 Causal Templates JSON Structure

```json
{
  "templates": [
    {
      "id": "dtcc_liquidity",
      "name": "Public Investment → Liquidity Squeeze",
      "name_vi": "Đầu tư công → Thanh khoản căng",
      "region": "vietnam",
      "trigger_keywords": ["đầu tư công", "giải ngân", "ĐTCC", "KBNN", "vốn ngân sách", "public investment"],
      "chain": [
        {"step": 1, "event": "Public investment disbursement increases", "event_vi": "Giải ngân đầu tư công tăng mạnh", "verified_by": "MoF data"},
        {"step": 2, "event": "State Treasury withdraws deposits from banks", "event_vi": "KBNN rút tiền gửi từ hệ thống NH", "verified_by": "SBV liquidity data"},
        {"step": 3, "event": "Interbank liquidity tightens", "event_vi": "Thanh khoản liên ngân hàng căng", "verified_by": "Interbank rate"},
        {"step": 4, "event": "Banks raise deposit rates", "event_vi": "Ngân hàng tăng lãi suất huy động", "verified_by": "Bank announcements"}
      ],
      "affected_indicators": ["interbank_on", "interbank_1w", "deposit_rate", "omo_net_daily"],
      "typical_lag": "1-2 weeks"
    },
    {
      "id": "fed_vnd_pressure",
      "name": "Fed Hawkish → VND Pressure",
      "name_vi": "Fed hawkish → Áp lực VND",
      "region": "global",
      "trigger_keywords": ["Fed", "FOMC", "Powell", "rate hike", "hawkish", "dot plot"],
      "chain": [
        {"step": 1, "event": "Fed signals hawkish stance", "verified_by": "FOMC statement"},
        {"step": 2, "event": "US Treasury yields rise", "verified_by": "US10Y"},
        {"step": 3, "event": "DXY strengthens", "verified_by": "DXY index"},
        {"step": 4, "event": "EM currencies under pressure", "verified_by": "EM FX basket"},
        {"step": 5, "event": "VND depreciation pressure", "verified_by": "USD/VND rate"}
      ],
      "affected_indicators": ["fed_rate", "us10y", "dxy", "usd_vnd_central"],
      "impact_on_vietnam": "VND pressure limits room for domestic rate cuts",
      "typical_lag": "immediate to 1 week"
    },
    {
      "id": "omo_injection",
      "name": "SBV OMO Injection → Liquidity Support",
      "name_vi": "SBV bơm OMO → Hỗ trợ thanh khoản",
      "region": "vietnam",
      "trigger_keywords": ["OMO", "nghiệp vụ thị trường mở", "bơm ròng", "hút ròng", "SBV", "open market"],
      "chain": [
        {"step": 1, "event": "SBV net injects via OMO", "event_vi": "SBV bơm ròng qua OMO", "verified_by": "SBV OMO data"},
        {"step": 2, "event": "Banking system liquidity improves", "event_vi": "Thanh khoản hệ thống cải thiện", "verified_by": "Interbank rate"},
        {"step": 3, "event": "Short-term rates stabilize/decrease", "event_vi": "Lãi suất ngắn hạn ổn định/giảm", "verified_by": "ON/1W rates"}
      ],
      "affected_indicators": ["omo_net_daily", "interbank_on", "interbank_1w"],
      "typical_lag": "immediate"
    },
    {
      "id": "tt02_npl",
      "name": "Circular 02 Expiry → NPL Surge",
      "name_vi": "TT02 hết hiệu lực → NPL tăng",
      "region": "vietnam",
      "trigger_keywords": ["thông tư 02", "TT02", "nợ xấu", "NPL", "tái cơ cấu nợ", "trích lập dự phòng", "circular 02"],
      "chain": [
        {"step": 1, "event": "Circular 02 expires", "event_vi": "Thông tư 02 hết hiệu lực", "verified_by": "SBV announcement"},
        {"step": 2, "event": "Banks must recognize actual NPL", "event_vi": "NH phải ghi nhận nợ xấu thực", "verified_by": "Bank reports"},
        {"step": 3, "event": "NPL ratio spikes", "event_vi": "Tỷ lệ NPL tăng đột biến", "verified_by": "NPL data"},
        {"step": 4, "event": "Provisioning pressure increases", "event_vi": "Áp lực trích lập dự phòng", "verified_by": "Bank financials"},
        {"step": 5, "event": "Bank profits may decline", "event_vi": "Lợi nhuận NH có thể giảm", "verified_by": "Quarterly results"}
      ],
      "affected_indicators": ["npl_ratio", "bank_provisions"],
      "typical_lag": "1 quarter"
    },
    {
      "id": "china_slowdown_export",
      "name": "China Slowdown → VN Export Risk",
      "name_vi": "Trung Quốc chậm lại → Rủi ro xuất khẩu VN",
      "region": "global",
      "trigger_keywords": ["China PMI", "Trung Quốc", "sản xuất Trung Quốc", "xuất khẩu sang Trung Quốc"],
      "chain": [
        {"step": 1, "event": "China manufacturing PMI contracts", "verified_by": "NBS/Caixin PMI"},
        {"step": 2, "event": "Industrial commodity demand weakens", "verified_by": "Copper, steel prices"},
        {"step": 3, "event": "Vietnam exports to China may slow", "verified_by": "GSO export data"}
      ],
      "affected_indicators": ["china_pmi", "copper_price", "vn_export_china"],
      "impact_on_vietnam": "VN exports to China ~17% of total - monitor closely",
      "typical_lag": "1-2 months"
    }
  ]
}
```

---

## 4. CRAWLER SPECIFICATIONS

### ⚠️ COLLABORATIVE WORKFLOW
**IMPORTANT FOR COPILOT**: Crawler development requires collaboration with user.

For EACH crawler:
1. Define expected data structure
2. **STOP and ask user** for sample cURL + response
3. Wait for feedback before implementing
4. Implement based on actual response
5. Test and iterate

### 4.1 SBV Crawler (sbv_crawler.py) - ACTIVE

**Status**: User has provided sample data. Ready to implement.

**Data Types from SBV**:
| Type | Description | Frequency |
|------|-------------|-----------|
| `exchange_rate` | USD/VND central rate | Daily |
| `gold_price` | SJC gold prices | Daily |
| `policy_rate` | Rediscount, refinancing rates | On change |
| `interbank_rate` | ON, 1W, 2W, 1M, 3M, 6M, 9M rates | Daily |
| `cpi` | Monthly CPI data | Monthly |
| `omo` | Open market operations | Daily |
| `news` | SBV announcements | As published |

**OMO Data Structure** (from user):
```python
@dataclass
class OMORecord:
    name: str
    transaction_type: str       # "Mua kỳ hạn" (inject) or "Bán kỳ hạn" (withdraw)
    auction_round: int          # 1, 2, 3, 4...
    term: str                   # "7 ngày", "28 ngày", "56 ngày", "Tổng cộng"
    participants: str           # "13/13"
    volume: float               # Billion VND
    interest_rate: float        # %
    date: str                   # "2026-02-03"
    is_total: bool              # True for summary rows
    source: str
    source_url: str

# Aggregation logic
def aggregate_omo_daily(records: list) -> dict:
    """
    Aggregate OMO by date.
    Only use records where is_total=True and term="Tổng cộng"
    
    Returns:
    {
        "2026-02-03": {
            "inject": 80926.88,      # Sum of all "Mua kỳ hạn" totals
            "withdraw": 0,            # Sum of all "Bán kỳ hạn" totals (if any)
            "net": 80926.88,          # inject - withdraw
            "by_term": {
                "7d": 40731.40,
                "28d": 24581.58,
                "56d": 15613.90
            }
        }
    }
    
    NOTE: "Bán kỳ hạn" (reverse repo/withdraw) data is not available from 
    SBV direct source. If withdraw=0, it means no data, not necessarily 
    zero withdrawals. TODO: Find alternative source for reverse repo data.
    """
```

**Interbank Rate Structure**:
```python
@dataclass  
class InterbankRate:
    term: str              # "Qua đêm", "1 Tuần", "2 Tuần", etc.
    avg_rate: float        # %
    volume: float          # Billion VND
    date: str
    source: str

# Mapping to indicator IDs
INTERBANK_TERM_MAP = {
    "Qua đêm": "interbank_on",
    "1 Tuần": "interbank_1w", 
    "2 Tuần": "interbank_2w",
    "1 Tháng": "interbank_1m",
    "3 Tháng": "interbank_3m",
    "6 Tháng": "interbank_6m",
    "9 Tháng": "interbank_9m"
}
```

**Saving Logic for Indicator History**:
```python
def save_indicator_if_changed(indicator_id: str, new_value: float, date: str):
    """
    Only save if value changed from previous record.
    Cronjob runs hourly - avoid duplicates.
    """
    latest = db.query(
        "SELECT value FROM indicator_history WHERE indicator_id = ? ORDER BY recorded_at DESC LIMIT 1",
        [indicator_id]
    )
    if not latest or latest.value != new_value:
        db.insert_indicator_history(indicator_id, new_value, date)
```

### 4.2 News Crawler (news_crawler.py) - TODO
- **Sources**: VnEconomy RSS, CafeF RSS, VnExpress - TBD
- **Status**: Not implemented yet

### 4.3 Calendar Crawler (calendar_crawler.py) - TODO
- **Source**: investing.com, forexfactory - TBD
- **Status**: Not implemented yet

### 4.4 Global Crawler (global_crawler.py) - TODO
- **Sources**: Yahoo Finance, FRED API - TBD
- **Status**: Not implemented yet

---

## 5. LLM PROCESSOR SPECIFICATIONS

### 5.1 Multi-Layer Pipeline

```
Raw News/Data
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 1: CLASSIFICATION                                 │
│  - is_market_relevant: yes/no                           │
│  - category: monetary/fiscal/banking/...                │
│  - linked_indicators: [indicator_ids]                   │
│                                                          │
│  Output: Classified news, irrelevant filtered out       │
└─────────────────────────────────────────────────────────┘
      │
      ▼ (only relevant news)
┌─────────────────────────────────────────────────────────┐
│  LAYER 2: SCORING                                        │
│  - base_score: 1-100                                    │
│  - score_factors breakdown                              │
│  - causal_analysis                                      │
│  - creates/resolves investigations                      │
│                                                          │
│  Input includes: previous context, open investigations  │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 3: RANKING & DECAY (Daily)                        │
│  - Apply time decay to all active news                  │
│  - Apply boost factors                                  │
│  - Assign display_section                               │
│  - Identify hot topics                                  │
│                                                          │
│  Runs on ALL active events, not just today's           │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  INVESTIGATION REVIEW (Separate process)                 │
│  - Review open investigations                           │
│  - Check for new evidence                               │
│  - Update statuses                                      │
│  - Mark stale items                                     │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Layer 1: Classification Prompt

```python
CLASSIFICATION_PROMPT = """
You are a financial news classifier for Vietnam market intelligence.

## NEWS ARTICLE
{article}

## TASK
Classify this news article. Output JSON only:

```json
{
  "is_market_relevant": true/false,
  "category": "monetary|fiscal|banking|economic|geopolitical|corporate|regulatory|internal",
  "linked_indicators": ["indicator_id_1", "indicator_id_2"] or [],
  "reasoning": "Brief explanation (1 sentence)"
}
```

## CLASSIFICATION RULES

**is_market_relevant = TRUE if:**
- News could affect any financial indicator (rates, FX, inflation)
- Policy changes or announcements
- Economic data releases
- Bank/corporate financial results with market impact

**is_market_relevant = FALSE if:**
- Internal organizational activities (conferences, youth union, appointments)
- Ceremonial events
- General news without market implications

**AVAILABLE INDICATORS:**
- interbank_on, interbank_1w (Interbank rates)
- omo_net_daily (OMO operations)
- usd_vnd_central (Exchange rate)
- cpi_mom, cpi_yoy (Inflation)
- gold_sjc (Gold price)
- rediscount_rate, refinancing_rate (Policy rates)
- fed_rate, dxy, us10y (Global - TODO)

**CATEGORIES:**
- monetary: OMO, interest rates, liquidity, central bank policy
- fiscal: Public investment, budget, tax policy
- banking: NPL, credit growth, bank financials
- economic: GDP, CPI, trade data
- geopolitical: Trade tensions, sanctions
- corporate: Company news (non-bank)
- regulatory: New regulations, circulars
- internal: SBV/government internal activities
"""
```

### 5.3 Layer 2: Scoring Prompt

```python
SCORING_PROMPT = """
You are a senior financial analyst scoring market-relevant news for Vietnam.

## NEWS ARTICLE
Title: {title}
Content: {content}
Category: {category}
Linked Indicators: {linked_indicators}

## CONTEXT FROM PREVIOUS ANALYSIS (Last 30 days)
{previous_context_summary}

## OPEN INVESTIGATIONS
{open_investigations}

## CAUSAL TEMPLATES
{causal_templates}

## TASK
Score and analyze this news. Output JSON:

```json
{
  "base_score": 1-100,
  "score_factors": {
    "direct_indicator_impact": 0-30,
    "policy_significance": 0-25,
    "market_breadth": 0-20,
    "novelty": 0-15,
    "source_authority": 0-10
  },
  
  "causal_analysis": {
    "matched_template_id": "template_id or null",
    "chain": [
      {"step": 1, "event": "...", "status": "verified|likely|uncertain"}
    ],
    "confidence": "verified|likely|uncertain",
    "reasoning": "Explain the causal logic"
  },
  
  "is_follow_up": true/false,
  "follows_up_on": "investigation_id or event_id if follow-up",
  
  "investigation_action": {
    "resolves": "investigation_id or null",
    "resolution": "How this resolves it",
    "creates_new": true/false,
    "new_investigation": {
      "question": "What needs to be investigated?",
      "priority": "high|medium|low",
      "what_to_look_for": "Specific things to watch for"
    }
  },
  
  "predictions": [
    {
      "prediction": "Specific, testable prediction",
      "confidence": "high|medium|low",
      "check_by_date": "YYYY-MM-DD",
      "verification_indicator": "indicator_id"
    }
  ]
}
```

## SCORING GUIDELINES

**Base Score Ranges:**
- 80-100: Major policy change, direct rate/FX impact, breaking news
- 60-79: Significant news, clear indicator implications
- 40-59: Moderate relevance, indirect/future impact
- 20-39: Minor news, contextual information
- 1-19: Marginally relevant

**Score Factors:**
- direct_indicator_impact (0-30): Will this move a specific indicator?
- policy_significance (0-25): Is this a policy change or signal?
- market_breadth (0-20): How many market segments affected?
- novelty (0-15): Is this new information or repeat of known facts?
- source_authority (0-10): How authoritative is the source?

**Investigation Rules:**
- If news answers an open investigation question → resolves
- If news raises unanswered questions → creates_new
- Prioritize high if affects interest rates, FX, or major policy
"""
```

### 5.4 Layer 3: Ranking & Decay Prompt

```python
RANKING_PROMPT = """
You are reviewing ALL active news for final ranking and display.

## TODAY'S DATE
{today}

## ALL ACTIVE EVENTS (sorted by current_score DESC)
{all_active_events}

## TASKS

1. **Apply Time Decay:**
   - Day 0 (today): 100%
   - Day 1-3: 90%
   - Day 4-7: 70%
   - Day 8-14: 50%
   - Day 15-30: 30%
   - Day 30+: Archive

2. **Apply Boost Factors:**
   - Follow-up to open investigation: +20%
   - Part of hot topic (3+ in 7 days): +15%
   - Connects 2+ indicators: +10%

3. **Assign Display Sections:**
   - key_events: final_score >= 50 AND linked_indicators not empty
   - other_news: is_market_relevant = true AND final_score >= 20
   - archive: final_score < 20 OR age > 30 days

4. **Identify Hot Topics:**
   - Topic appears 3+ times in 7 days → hot topic
   - Flag related events

## OUTPUT JSON
```json
{
  "rankings": [
    {
      "event_id": "...",
      "age_days": 2,
      "original_score": 75,
      "decay_factor": 0.9,
      "boost_factor": 1.15,
      "final_score": 77.6,
      "display_section": "key_events|other_news|archive",
      "hot_topic_badge": "topic_name or null"
    }
  ],
  
  "hot_topics": [
    {
      "topic": "interbank liquidity",
      "count_7d": 5,
      "trend": "increasing|stable|decreasing",
      "related_event_ids": ["evt_1", "evt_2"]
    }
  ],
  
  "section_summary": {
    "key_events_count": 5,
    "other_news_count": 12,
    "archived_count": 3
  }
}
```

## DISPLAY RULES
- key_events: Sorted by final_score DESC
- other_news: Sorted by published_at DESC (newest first)
- Maximum 15 items in key_events
- other_news collapsed by default in UI
"""
```

### 5.5 Investigation Review Prompt

```python
INVESTIGATION_REVIEW_PROMPT = """
You are reviewing open investigations for status updates.

## TODAY'S DATE
{today}

## OPEN INVESTIGATIONS
{open_investigations}

## TODAY'S NEWS (already scored)
{todays_events}

## CURRENT INDICATORS
{current_indicators}

## TASK
Review each investigation and determine updates.

## OUTPUT JSON
```json
{
  "investigation_updates": [
    {
      "investigation_id": "inv_001",
      "previous_status": "open",
      "new_status": "open|updated|resolved|stale|escalated",
      
      "evidence_today": [
        {
          "event_id": "evt_xxx",
          "evidence_type": "supports|contradicts|neutral",
          "summary": "What this evidence shows..."
        }
      ],
      
      "updated_evidence_summary": "Overall evidence summary...",
      
      "resolution": "Only if resolved - the answer",
      "resolution_confidence": "high|medium|low",
      
      "reasoning": "Why this status"
    }
  ],
  
  "stale_check": [
    {
      "investigation_id": "inv_002",
      "days_without_update": 15,
      "recommendation": "close|escalate|keep",
      "reason": "..."
    }
  ]
}
```

## STATUS DEFINITIONS
- **open**: No new evidence, continue monitoring
- **updated**: New evidence found, but not conclusive
- **resolved**: Clear answer found
- **stale**: No updates for 14+ days, consider closing
- **escalated**: Conflicting evidence, needs human review

## RULES
- Only mark "resolved" if evidence clearly answers the question
- "updated" requires actual new information, not just related news
- After 14 days with no updates → recommend stale
- If evidence conflicts → escalate for human review
"""
```

### 5.6 Context Builder

```python
def build_previous_context(db, lookback_days: int = 30) -> dict:
    """
    Build context from previous runs for LLM continuity.
    """
    return {
        "lookback_days": lookback_days,
        "last_run_summary": get_last_run_summary(db),
        "open_investigations": get_open_investigations(db),
        "recurring_topics": get_topics_with_count_gte(db, min_count=3, days=7),
        "recent_predictions": get_pending_predictions(db),
        "key_events_summary": summarize_key_events(db, days=lookback_days),
        "indicator_trends": get_indicator_trends(db, days=7)
    }
```

### 5.7 Processing Flow

```python
def run_analysis_pipeline():
    """Main processing pipeline - runs on schedule"""
    
    # 1. Fetch new data
    raw_data = sbv_crawler.fetch()
    
    # 2. Update indicators
    update_indicators(raw_data)
    save_indicator_history(raw_data)
    
    # 3. Extract news from raw data
    news_items = extract_news(raw_data)
    
    # 4. Layer 1: Classify
    classified = []
    for news in news_items:
        result = llm.generate(CLASSIFICATION_PROMPT.format(article=news))
        classified.append({**news, **parse_json(result)})
    
    # 5. Filter relevant only
    relevant = [n for n in classified if n['is_market_relevant']]
    
    # 6. Build context
    context = build_previous_context(db, lookback_days=30)
    context_summary = llm.generate(CONTEXT_SUMMARY_PROMPT.format(**context))
    
    # 7. Layer 2: Score each relevant news
    scored = []
    for news in relevant:
        result = llm.generate(SCORING_PROMPT.format(
            title=news['title'],
            content=news['content'],
            category=news['category'],
            linked_indicators=news['linked_indicators'],
            previous_context_summary=context_summary,
            open_investigations=context['open_investigations'],
            causal_templates=load_templates()
        ))
        scored.append({**news, **parse_json(result)})
    
    # 8. Save to database
    save_events(scored)
    process_investigation_actions(scored)
    
    # 9. Layer 3: Rank ALL active events
    all_active = get_active_events(db, max_age_days=30)
    ranking_result = llm.generate(RANKING_PROMPT.format(
        today=today(),
        all_active_events=all_active
    ))
    apply_rankings(parse_json(ranking_result))
    
    # 10. Review investigations
    investigation_result = llm.generate(INVESTIGATION_REVIEW_PROMPT.format(
        today=today(),
        open_investigations=context['open_investigations'],
        todays_events=scored,
        current_indicators=get_current_indicators(db)
    ))
    update_investigations(parse_json(investigation_result))
    
    # 11. Save run history
    save_run_history(stats)
```

---

## 6. API ENDPOINTS

```python
# FastAPI routes

# Health
GET  /api/health

# Indicators
GET  /api/indicators                     # List all, grouped by category
GET  /api/indicators/{id}                # Single indicator with history
GET  /api/indicators/category/{cat}      # Filter by category
GET  /api/indicators/{id}/history        # Historical data for charts

# Events
GET  /api/events                         # List with pagination & filters
GET  /api/events/key                     # display_section = 'key_events'
GET  /api/events/other                   # display_section = 'other_news', sorted by date DESC
GET  /api/events/{id}                    # Single event with full analysis
GET  /api/events/today                   # Today's events only

# Investigations
GET  /api/investigations                 # List open investigations
GET  /api/investigations/all             # Include resolved, stale
GET  /api/investigations/{id}            # Single with evidence timeline
GET  /api/investigations/{id}/evidence   # All evidence for investigation
POST /api/investigations/{id}/resolve    # Manual resolve (human review)

# Topics
GET  /api/topics/hot                     # Hot topics (3+ in 7 days)
GET  /api/topics/{topic}/events          # Events related to topic

# Calendar
GET  /api/calendar                       # Upcoming events
GET  /api/calendar/week                  # This week

# System
GET  /api/runs                           # Processing run history
GET  /api/runs/latest                    # Latest run summary
POST /api/refresh                        # Manual trigger refresh
```

---

## 7. FRONTEND SPECIFICATIONS

### 7.1 Main Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Header: Market Intelligence Dashboard    [Last Update: 14:30]  [⟳]     │
├─────────────────────────────────────────────────────────────────────────┤
│ Tabs: [🇻🇳 Vietnam] [🌍 Global] [📋 All News] [🔍 Investigations]       │
├────────────────┬────────────────────────────┬───────────────────────────┤
│                │                            │                           │
│  KEY           │  🔥 KEY EVENTS             │  📅 UPCOMING CALENDAR     │
│  INDICATORS    │  (sorted by final_score)   │                           │
│                │                            │  - FOMC Meeting (Feb 12)  │
│  ┌──────────┐  │  ┌────────────────────┐   │  - US CPI (Feb 14)        │
│  │🏦 Monetary│  │  │ [85] SBV injects   │   │  - VN CPI (Feb 20)        │
│  │          │  │  │ 80,926B via OMO    │   │                           │
│  │ OMO Net  │  │  │ 🔥 Hot: liquidity  │   ├───────────────────────────┤
│  │ +80,926B │  │  │ 📊 interbank_on    │   │                           │
│  │          │  │  └────────────────────┘   │  🔍 INVESTIGATIONS        │
│  │ ON Rate  │  │                            │                           │
│  │ 9.12% ↑  │  │  ┌────────────────────┐   │  ⚡ HIGH PRIORITY (2)     │
│  │          │  │  │ [72] Governor on   │   │  ┌─────────────────────┐  │
│  │ 1W Rate  │  │  │ credit quality     │   │  │ Will deposit rates  │  │
│  │ 9.56% ↑  │  │  │ 🔗 Follows: inv_01 │   │  │ increase?           │  │
│  └──────────┘  │  │ 📊 npl_ratio       │   │  │ Status: 🟡 UPDATED  │  │
│                │  └────────────────────┘   │  │ Evidence: 3         │  │
│  ┌──────────┐  │                            │  └─────────────────────┘  │
│  │💱 Forex  │  │  ... more key events ...  │                           │
│  │          │  │                            │  📋 MEDIUM (3)            │
│  │ USD/VND  │  ├────────────────────────────┤  [collapsed]              │
│  │ 25,067   │  │                            │                           │
│  └──────────┘  │  📰 OTHER NEWS             │  ✅ RECENTLY RESOLVED     │
│                │  (collapsed, sorted by     │  [collapsed]              │
│  ┌──────────┐  │   date DESC)               │                           │
│  │📈 CPI    │  │                            │                           │
│  │          │  │  ▶ [Click to expand]       │                           │
│  │ MoM:     │  │    - SBV conference...     │                           │
│  │ +0.19%   │  │    - Youth union...        │                           │
│  └──────────┘  │    - SEA Group meeting...  │                           │
│                │                            │                           │
└────────────────┴────────────────────────────┴───────────────────────────┘
│ Footer: Sources: 1 | Events today: 5 | Open investigations: 5          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Event Detail (when clicked)

```
┌─────────────────────────────────────────────────────────────────┐
│ EVENT DETAIL                                            [Close] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ SBV injects 80,926 billion VND via OMO                          │
│ Score: 85 | Category: monetary | Source: SBV                    │
│                                                                  │
│ ─────────────────────────────────────────────────────────────── │
│                                                                  │
│ 📊 LINKED INDICATORS                                            │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │
│ │ OMO Net     │ │ ON Rate     │ │ 1W Rate     │                │
│ │ +80,926B    │ │ 9.12%       │ │ 9.56%       │                │
│ └─────────────┘ └─────────────┘ └─────────────┘                │
│                                                                  │
│ 🔗 CAUSAL CHAIN (Template: omo_injection)                       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ✓ Step 1: SBV net injects via OMO          [VERIFIED]       │ │
│ │     ↓                                                        │ │
│ │ ? Step 2: Banking liquidity improves        [LIKELY]        │ │
│ │     ↓                                                        │ │
│ │ ? Step 3: Short-term rates stabilize        [UNCERTAIN]     │ │
│ │                                                              │ │
│ │ 🔍 Needs Investigation:                                      │ │
│ │    - Will ON rate decrease tomorrow?                        │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ 📈 PREDICTIONS                                                  │
│ • ON rate may decrease to 8.5-9.0% by Feb 7                    │
│   Confidence: Medium | Check by: 2026-02-07                    │
│                                                                  │
│ 🔗 RELATED EVENTS                                               │
│ • [Feb 2] DTCC disbursement increases (follows)                │
│ • [Feb 1] Liquidity tightens end of month                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 Investigation Detail

```
┌─────────────────────────────────────────────────────────────────┐
│ INVESTIGATION: Will deposit rates increase?             [Close] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Status: 🟡 UPDATED          Priority: ⚡ HIGH                   │
│ Created: Feb 2, 2026        Last Evidence: Feb 4, 2026          │
│                                                                  │
│ ─────────────────────────────────────────────────────────────── │
│                                                                  │
│ 📋 QUESTION                                                     │
│ Will commercial banks raise deposit rates in the next 2 weeks  │
│ given tightening interbank liquidity?                          │
│                                                                  │
│ 🔍 WHAT TO LOOK FOR                                             │
│ • Bank announcements on rate changes                           │
│ • Deposit rate comparison data                                 │
│ • SBV guidance on rates                                        │
│                                                                  │
│ ─────────────────────────────────────────────────────────────── │
│                                                                  │
│ 📊 EVIDENCE TIMELINE                                            │
│                                                                  │
│ Feb 4 ──●── [SUPPORTS] OMO injection 80,926B                   │
│         │   "Large injection suggests SBV aware of pressure"   │
│         │                                                       │
│ Feb 3 ──●── [SUPPORTS] ON rate rises to 9.12%                  │
│         │   "Elevated interbank rate confirms tight liquidity" │
│         │                                                       │
│ Feb 2 ──●── [SUPPORTS] DTCC disbursement +45%                  │
│             "Public investment draws liquidity from banks"     │
│                                                                  │
│ ─────────────────────────────────────────────────────────────── │
│                                                                  │
│ 📝 EVIDENCE SUMMARY                                             │
│ 3 pieces of evidence all support the hypothesis. Interbank     │
│ rates elevated, SBV responding with OMO. Banks may need to     │
│ raise deposit rates to attract funding.                        │
│                                                                  │
│ [Mark Resolved] [Escalate] [Add Manual Note]                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. IMPLEMENTATION TASKS

### Task 1: Project Setup & Data Foundation
- [ ] Set up project structure
- [ ] Create SQLite schema (all tables)
- [ ] Implement database utilities
- [ ] Create causal_templates.json

### Task 2: SBV Crawler (ACTIVE)
- [ ] Implement sbv_crawler.py based on user's data structure
- [ ] Implement OMO aggregation logic
- [ ] Implement indicator saving with history
- [ ] Handle "Bán kỳ hạn" as null/unknown (TODO: find source)
- [ ] Test with provided sample data

### Task 3: LLM Processor
- [ ] Set up Claude API integration
- [ ] Implement Layer 1: classifier.py
- [ ] Implement Layer 2: scorer.py
- [ ] Implement Layer 3: ranker.py
- [ ] Implement investigation_reviewer.py
- [ ] Implement context_builder.py
- [ ] Implement output_parser.py with validation
- [ ] Test pipeline with sample data

### Task 4: API Layer
- [ ] Set up FastAPI
- [ ] Implement indicator endpoints
- [ ] Implement event endpoints
- [ ] Implement investigation endpoints
- [ ] Add error handling

### Task 5: Frontend
- [ ] Create React app with Vite
- [ ] Implement main dashboard layout
- [ ] Implement indicator panels
- [ ] Implement key events list
- [ ] Implement other news (collapsed)
- [ ] Implement investigation panel
- [ ] Implement event detail modal
- [ ] Implement investigation detail modal

### Task 6: Automation & Polish
- [ ] Set up scheduler
- [ ] Add logging
- [ ] Error recovery
- [ ] Deploy

### Future Tasks (TODO)
- [ ] News crawler (RSS feeds)
- [ ] Calendar crawler
- [ ] Global data crawler
- [ ] "Bán kỳ hạn" data source
- [ ] Additional causal templates
- [ ] Performance analytics

---

## 9. IMPORTANT NOTES FOR COPILOT

### DO:
- **STOP and ask user** when implementing new crawlers
- Keep code simple and readable
- Use type hints in Python
- Add docstrings to functions
- Handle errors gracefully
- Log important operations
- Use environment variables for API keys
- Test each component before moving on
- Mark TODO items clearly in code

### DON'T:
- Implement crawlers without user data
- Over-engineer
- Use async unless necessary
- Add features not in spec
- Use embedding/vector search (not for v1)
- Assume data structures

### Error Handling:
- Crawler fails → Log, continue with others
- LLM fails → Retry once, save raw for manual review
- DB fails → Critical, stop and alert
- Context build fails → Run with empty context, log warning

### Collaborative Checkpoints:
- [ ] After each crawler implementation → User tests
- [ ] After LLM prompts → User reviews output quality
- [ ] After API endpoints → User tests
- [ ] After frontend components → User reviews UI

---

## 10. ENVIRONMENT VARIABLES

```env
ANTHROPIC_API_KEY=your_claude_api_key
DATABASE_PATH=./data/market.db
LOG_LEVEL=INFO
CRAWLER_INTERVAL_HOURS=1
LLM_MODEL=claude-sonnet-4-20250514
CONTEXT_LOOKBACK_DAYS=30
MAX_KEY_EVENTS=15
DECAY_ARCHIVE_DAYS=30
```

---

## 11. TODO LIST

### Data Sources
- [ ] **OMO Reverse Repo**: "Bán kỳ hạn" data not available from SBV. Need alternative source. Currently treating as null/0.
- [ ] **News Sources**: VnEconomy, CafeF RSS feeds - need to implement
- [ ] **Economic Calendar**: investing.com or forexfactory - need to implement
- [ ] **Global Data**: Fed rate, DXY, US10Y, Brent - need Yahoo Finance or FRED API

### Features
- [ ] Prediction tracking and accuracy scoring
- [ ] Email/notification alerts for high-impact events
- [ ] Export functionality (PDF reports)
- [ ] Historical analysis view
- [ ] Indicator correlation analysis

### Technical
- [ ] Rate limiting for LLM calls
- [ ] Caching for repeated queries
- [ ] Database backup strategy
- [ ] Monitoring and alerting