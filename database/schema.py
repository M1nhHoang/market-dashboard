"""
Database Schema Definitions

Contains all SQL CREATE statements for the Market Intelligence database.
Schema based on coding_plan.prompt.instructions.md specification.
"""

# ============================================
# INDICATORS SCHEMA
# ============================================

INDICATORS_SCHEMA = """
-- Current indicator values
CREATE TABLE IF NOT EXISTS indicators (
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
CREATE TABLE IF NOT EXISTS indicator_history (
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

CREATE INDEX IF NOT EXISTS idx_indicator_history_lookup 
ON indicator_history(indicator_id, date DESC);
"""


# ============================================
# EVENTS SCHEMA
# ============================================

EVENTS_SCHEMA = """
-- Extracted news events
CREATE TABLE IF NOT EXISTS events (
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

CREATE INDEX IF NOT EXISTS idx_events_display ON events(display_section, current_score DESC);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_run_date ON events(run_date);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);

-- Causal analysis for events
CREATE TABLE IF NOT EXISTS causal_analyses (
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

-- Topic frequency tracking
CREATE TABLE IF NOT EXISTS topic_frequency (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    category TEXT,
    occurrence_count INTEGER DEFAULT 1,
    first_seen DATE,
    last_seen DATE,
    related_event_ids TEXT,           -- JSON array
    is_hot BOOLEAN DEFAULT FALSE      -- 3+ occurrences in 7 days
);

CREATE INDEX IF NOT EXISTS idx_topic_frequency_topic ON topic_frequency(topic);

-- Score history for analysis
CREATE TABLE IF NOT EXISTS score_history (
    id TEXT PRIMARY KEY,
    event_id TEXT REFERENCES events(id),
    score REAL,
    decay_factor REAL,
    boost_factor REAL,
    display_section TEXT,
    recorded_at TIMESTAMP
);
"""


# ============================================
# INVESTIGATIONS SCHEMA
# ============================================

INVESTIGATIONS_SCHEMA = """
-- Investigation tracking
CREATE TABLE IF NOT EXISTS investigations (
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

CREATE INDEX IF NOT EXISTS idx_investigations_status ON investigations(status);

-- Evidence for investigations
CREATE TABLE IF NOT EXISTS investigation_evidence (
    id TEXT PRIMARY KEY,
    investigation_id TEXT REFERENCES investigations(id),
    event_id TEXT REFERENCES events(id),
    evidence_type TEXT,               -- 'supports', 'contradicts', 'neutral'
    summary TEXT,
    added_at TIMESTAMP
);

-- Predictions from analysis
CREATE TABLE IF NOT EXISTS predictions (
    id TEXT PRIMARY KEY,
    prediction TEXT NOT NULL,
    based_on_events TEXT,             -- JSON array of event_ids
    source_event_id TEXT,
    confidence TEXT,                  -- 'high', 'medium', 'low'
    check_by_date DATE,
    verification_indicator TEXT,      -- indicator_id to check
    status TEXT DEFAULT 'pending',    -- 'pending', 'verified', 'failed', 'expired'
    actual_outcome TEXT,
    verified_at TIMESTAMP,
    created_at TIMESTAMP
);
"""


# ============================================
# SYSTEM SCHEMA
# ============================================

SYSTEM_SCHEMA = """
-- Run history for tracking pipeline executions
CREATE TABLE IF NOT EXISTS run_history (
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

-- Economic calendar events
CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    date DATE,
    time TIME,
    event_name TEXT,
    country TEXT,
    importance TEXT,                  -- 'high', 'medium', 'low'
    forecast TEXT,
    previous TEXT,
    actual TEXT,
    created_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_events(date);
"""


# ============================================
# COMBINED SCHEMA
# ============================================

FULL_SCHEMA = INDICATORS_SCHEMA + EVENTS_SCHEMA + INVESTIGATIONS_SCHEMA + SYSTEM_SCHEMA
