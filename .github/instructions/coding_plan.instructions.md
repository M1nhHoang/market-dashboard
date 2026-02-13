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