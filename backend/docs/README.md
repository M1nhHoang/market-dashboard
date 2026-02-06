# Documentation

## Overview

Tài liệu kỹ thuật cho Market Intelligence Dashboard.

---

## Table of Contents

| Document | Description |
|----------|-------------|
| [database-schema.md](database-schema.md) | Schema chi tiết cho 11 tables, relationships, indexes |
| [data-flow.md](data-flow.md) | Pipeline flow từ crawlers → LLM → database → API → UI |
| [ui-mapping.md](ui-mapping.md) | Mapping giữa database tables và UI components |

---

## Quick Reference

### Database Tables (11)

| # | Table | Purpose |
|---|-------|---------|
| 1 | `indicators` | Giá trị hiện tại của các chỉ số |
| 2 | `indicator_history` | Lịch sử giá trị theo thời gian |
| 3 | `events` | Tin tức đã phân tích |
| 4 | `causal_analyses` | Phân tích chuỗi nhân quả |
| 5 | `topic_frequency` | Theo dõi tần suất topic |
| 6 | `score_history` | Lịch sử điểm số |
| 7 | `investigations` | Câu hỏi đang theo dõi |
| 8 | `investigation_evidence` | Evidence cho investigations |
| 9 | `predictions` | Dự đoán từ phân tích |
| 10 | `run_history` | Lịch sử pipeline runs |
| 11 | `calendar_events` | Lịch kinh tế sắp tới |

### Processing Layers

| Layer | Purpose | Input | Output |
|-------|---------|-------|--------|
| 1 | Classification | Raw news | `is_market_relevant`, `category`, `linked_indicators` |
| 2 | Scoring | Classified news + 30-day context | `base_score`, `causal_analysis`, `predictions` |
| 3 | Ranking | All active events | `current_score`, `display_section`, `hot_topic` |

### API Endpoints

```
GET /api/indicators           # Panel data
GET /api/events/key           # Key events list
GET /api/events/other         # Other news (collapsed)
GET /api/investigations       # Investigations panel
GET /api/calendar/week        # Calendar panel
```

---

## Architecture Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Crawlers  │────▶│  LLM Pipe   │────▶│  Database   │
│  (hourly)   │     │  (3 layers) │     │  (SQLite)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  FastAPI    │
                                        └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   React     │
                                        │  Dashboard  │
                                        └─────────────┘
```

---

## Getting Started

### Run Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "description"
```

### Run Pipeline

```bash
# Manual run
python scheduler.py

# Or via API
curl -X POST http://localhost:8000/api/refresh
```

---

## Tech Stack

- **Backend**: Python 3.10+, FastAPI
- **Database**: SQLite + SQLAlchemy 2.0
- **Migrations**: Alembic
- **LLM**: Claude API (Anthropic)
- **Scheduler**: APScheduler
- **Frontend**: React + Tailwind CSS
