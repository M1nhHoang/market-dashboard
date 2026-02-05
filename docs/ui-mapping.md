# UI Feature Mapping

## Overview

Tài liệu này mô tả mapping giữa database tables và các thành phần UI trên Dashboard.

---

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Header: Market Intelligence Dashboard    [Last Update: 14:30]    [⟳]       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tabs: [🇻🇳 Vietnam] [🌍 Global] [📋 All News] [🔍 Investigations]           │
├──────────────────┬─────────────────────────────┬────────────────────────────┤
│                  │                             │                            │
│  [A] INDICATORS  │  [B] KEY EVENTS             │  [C] CALENDAR              │
│      PANEL       │      LIST                   │                            │
│                  │                             ├────────────────────────────┤
│                  │                             │                            │
│                  │                             │  [D] INVESTIGATIONS        │
│                  │                             │      PANEL                 │
│                  │                             │                            │
│                  ├─────────────────────────────┤                            │
│                  │                             │                            │
│                  │  [E] OTHER NEWS             │                            │
│                  │      (collapsed)            │                            │
│                  │                             │                            │
└──────────────────┴─────────────────────────────┴────────────────────────────┘
│ Footer: Sources: 1 | Events today: 5 | Open investigations: 5              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## [A] Indicators Panel

### UI Component
```
┌──────────────────┐
│ 🏦 Monetary      │
│ ──────────────── │
│ OMO Net          │
│ +80,926B  ↑15%   │
│                  │
│ ON Rate          │
│ 9.12%    ↑0.15   │
│                  │
│ 1W Rate          │
│ 9.56%    ↑0.12   │
├──────────────────┤
│ 💱 Forex         │
│ ──────────────── │
│ USD/VND          │
│ 25,067   ↓12     │
├──────────────────┤
│ 📈 CPI           │
│ ──────────────── │
│ MoM: +0.19%      │
│ YoY: +3.51%      │
└──────────────────┘
```

### Data Source

| UI Element | Table | Columns |
|------------|-------|---------|
| Group header (🏦 Monetary) | constants/indicator_mappings.py | `INDICATOR_GROUPS[category].display_name` |
| Indicator name | `indicators` | `name`, `name_vi` |
| Current value | `indicators` | `value`, `unit` |
| Change | `indicators` | `change`, `change_pct` |
| Trend arrow | `indicators` | `trend` (up/down/stable) |
| Last updated | `indicators` | `updated_at` |

### API Endpoint
```
GET /api/indicators

Response:
{
  "vietnam_monetary": {
    "display_name": "🏦 Monetary",
    "indicators": [
      {
        "id": "omo_net_daily",
        "name": "OMO Net",
        "value": 80926.88,
        "unit": "tỷ VND",
        "change": 12345.0,
        "change_pct": 15.0,
        "trend": "up",
        "updated_at": "2026-02-05T14:00:00"
      }
    ]
  }
}
```

### Click Action → Indicator Detail Modal
```
┌─────────────────────────────────────────────────────────────────┐
│ INDICATOR: Interbank ON Rate                            [Close] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current: 9.12%     Change: +0.15 (↑1.67%)                      │
│  Source: SBV        Last Update: 14:00 today                    │
│                                                                  │
│  📈 7-Day Chart                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                                              ●              ││
│  │                                    ●────────●               ││
│  │                        ●──────────●                         ││
│  │            ●──────────●                                     ││
│  │  ●────────●                                                 ││
│  └─────────────────────────────────────────────────────────────┘│
│    Jan 30  Jan 31  Feb 1  Feb 2  Feb 3  Feb 4  Feb 5           │
│                                                                  │
│  📰 Related Events (3)                                          │
│  • [85] SBV injects 80,926B via OMO (today)                    │
│  • [72] Interbank liquidity tightens (Feb 3)                   │
│  • [65] DTCC disbursement increases (Feb 2)                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| UI Element | Table | Query |
|------------|-------|-------|
| Chart data | `indicator_history` | `WHERE indicator_id = ? ORDER BY date DESC LIMIT 7` |
| Related events | `events` | `WHERE linked_indicators LIKE '%"interbank_on"%'` |

---

## [B] Key Events List

### UI Component
```
┌────────────────────────────────────────────┐
│ 🔥 KEY EVENTS                              │
│                                            │
│ ┌────────────────────────────────────────┐ │
│ │ [85] SBV injects 80,926B via OMO       │ │
│ │ 🔥 Hot: liquidity                      │ │
│ │ 📊 interbank_on, omo_net_daily         │ │
│ │ ⏱ 2 hours ago                          │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ ┌────────────────────────────────────────┐ │
│ │ [72] Governor speaks on credit quality │ │
│ │ 🔗 Follows: inv_001                    │ │
│ │ 📊 npl_ratio                           │ │
│ │ ⏱ Yesterday                            │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ ... more events ...                        │
└────────────────────────────────────────────┘
```

### Data Source

| UI Element | Table | Column |
|------------|-------|--------|
| Score badge [85] | `events` | `current_score` |
| Title | `events` | `title` |
| Hot topic badge | `events` | `hot_topic` |
| Follow-up link | `events` | `is_follow_up`, `follows_up_on` |
| Linked indicators | `events` | `linked_indicators` (JSON) |
| Time ago | `events` | `published_at` |

### API Endpoint
```
GET /api/events/key

Response:
{
  "events": [
    {
      "id": "evt_001",
      "title": "SBV injects 80,926B via OMO",
      "current_score": 85,
      "hot_topic": "liquidity",
      "is_follow_up": false,
      "linked_indicators": ["interbank_on", "omo_net_daily"],
      "published_at": "2026-02-05T10:30:00",
      "category": "monetary"
    }
  ],
  "total": 5
}
```

### Click Action → Event Detail Modal
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
│ 📄 SUMMARY                                                      │
│ Ngân hàng Nhà nước bơm ròng 80,926 tỷ đồng qua kênh thị        │
│ trường mở, hỗ trợ thanh khoản hệ thống...                       │
│                                                                  │
│ ─────────────────────────────────────────────────────────────── │
│                                                                  │
│ 📊 LINKED INDICATORS                                            │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │
│ │ OMO Net     │ │ ON Rate     │ │ 1W Rate     │                │
│ │ +80,926B    │ │ 9.12%       │ │ 9.56%       │                │
│ └─────────────┘ └─────────────┘ └─────────────┘                │
│                                                                  │
│ ─────────────────────────────────────────────────────────────── │
│                                                                  │
│ 🔗 CAUSAL CHAIN (Template: omo_injection)                       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ✓ Step 1: SBV net injects via OMO          [VERIFIED]       │ │
│ │     ↓                                                        │ │
│ │ ? Step 2: Banking liquidity improves        [LIKELY]        │ │
│ │     ↓                                                        │ │
│ │ ? Step 3: Short-term rates stabilize        [UNCERTAIN]     │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ ─────────────────────────────────────────────────────────────── │
│                                                                  │
│ 💯 SCORE BREAKDOWN                                              │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Direct Impact      ████████████████████░░░░░░░░░░  28/30   │ │
│ │ Policy Significance ██████████████████░░░░░░░░░░░  22/25   │ │
│ │ Market Breadth     █████████████████░░░░░░░░░░░░░  18/20   │ │
│ │ Novelty            █████████░░░░░░░░░░░░░░░░░░░░░  10/15   │ │
│ │ Source Authority   █████░░░░░░░░░░░░░░░░░░░░░░░░░   7/10   │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ ─────────────────────────────────────────────────────────────── │
│                                                                  │
│ 📈 PREDICTIONS                                                  │
│ • ON rate may decrease to 8.5-9.0% by Feb 7                    │
│   Confidence: Medium | Status: ⏳ Pending                      │
│                                                                  │
│ 🔗 RELATED EVENTS                                               │
│ • [Feb 2] DTCC disbursement increases (follows)                │
│ • [Feb 1] Liquidity tightens end of month                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| UI Element | Table | Column/Query |
|------------|-------|--------------|
| Summary | `events` | `summary` |
| Content | `events` | `content` |
| Score factors | `events` | `score_factors` (JSON) |
| Causal chain | `causal_analyses` | `chain_steps`, `confidence` |
| Template info | `causal_analyses` | `template_id` → lookup in `causal_templates.json` |
| Predictions | `predictions` | `WHERE source_event_id = ?` |
| Related events | `events` | Match by `linked_indicators` or `hot_topic` |

---

## [C] Calendar Panel

### UI Component
```
┌────────────────────────────────────────┐
│ 📅 UPCOMING CALENDAR                   │
│                                        │
│ Feb 7 (Wed)                            │
│ ├─ 🔴 US Jobless Claims (US)           │
│ └─ 🟡 VN Trade Balance (VN)            │
│                                        │
│ Feb 12 (Mon)                           │
│ └─ 🔴 FOMC Meeting (US)                │
│                                        │
│ Feb 14 (Wed)                           │
│ └─ 🔴 US CPI (US)                      │
│                                        │
│ Feb 20 (Thu)                           │
│ └─ 🔴 VN CPI (VN)                      │
│                                        │
└────────────────────────────────────────┘
```

### Data Source

| UI Element | Table | Column |
|------------|-------|--------|
| Date group | `calendar_events` | `date` |
| Event name | `calendar_events` | `event_name` |
| Country flag | `calendar_events` | `country` |
| Importance dot | `calendar_events` | `importance` (high=🔴, medium=🟡, low=⚪) |
| Time | `calendar_events` | `time` |

### API Endpoint
```
GET /api/calendar/week

Response:
{
  "events": [
    {
      "id": "cal_001",
      "date": "2026-02-07",
      "time": "08:30",
      "event_name": "US Jobless Claims",
      "country": "US",
      "importance": "high",
      "forecast": "220K",
      "previous": "218K"
    }
  ]
}
```

---

## [D] Investigations Panel

### UI Component
```
┌────────────────────────────────────────────┐
│ 🔍 INVESTIGATIONS                          │
│                                            │
│ ⚡ HIGH PRIORITY (2)                        │
│ ┌────────────────────────────────────────┐ │
│ │ Will deposit rates increase?           │ │
│ │ Status: 🟡 UPDATED                     │ │
│ │ Evidence: 3 | Last: today              │ │
│ └────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────┐ │
│ │ Is credit growth slowing?              │ │
│ │ Status: 🟢 OPEN                        │ │
│ │ Evidence: 1 | Last: Feb 3              │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ 📋 MEDIUM (3)                              │
│ ▶ [Click to expand]                        │
│                                            │
│ ✅ RECENTLY RESOLVED                        │
│ ▶ [Click to expand]                        │
│                                            │
└────────────────────────────────────────────┘
```

### Data Source

| UI Element | Table | Column |
|------------|-------|--------|
| Priority group | `investigations` | `priority` |
| Question | `investigations` | `question` |
| Status badge | `investigations` | `status` |
| Evidence count | `investigations` | `evidence_count` |
| Last evidence | `investigations` | `last_evidence_at` |

### Status Colors
```
🟢 OPEN     - Mới, chưa có evidence
🟡 UPDATED  - Có evidence mới
🔵 RESOLVED - Đã có câu trả lời
⚪ STALE    - Không có update > 14 ngày
🔴 ESCALATED - Cần human review
```

### API Endpoint
```
GET /api/investigations

Response:
{
  "high": [...],
  "medium": [...],
  "low": [...],
  "resolved": [...]
}
```

### Click Action → Investigation Detail Modal
```
┌─────────────────────────────────────────────────────────────────┐
│ INVESTIGATION: Will deposit rates increase?             [Close] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Status: 🟡 UPDATED          Priority: ⚡ HIGH                   │
│ Created: Feb 2, 2026        Last Evidence: Feb 5, 2026          │
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
│ Feb 5 ──●── [SUPPORTS] OMO injection 80,926B                   │
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
│ ─────────────────────────────────────────────────────────────── │
│                                                                  │
│ 📈 RELATED PREDICTIONS                                          │
│ • ON rate may decrease to 8.5-9.0% by Feb 7 (⏳ Pending)       │
│                                                                  │
│ [Mark Resolved] [Escalate] [Add Manual Note]                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| UI Element | Table | Query |
|------------|-------|-------|
| Evidence timeline | `investigation_evidence` | `WHERE investigation_id = ? ORDER BY added_at DESC` |
| Evidence event details | `events` | `JOIN events ON investigation_evidence.event_id = events.id` |
| Related predictions | `predictions` | `WHERE investigation_id = ?` |
| Evidence summary | `investigations` | `evidence_summary` |

---

## [E] Other News Section

### UI Component (Collapsed)
```
┌────────────────────────────────────────────┐
│ 📰 OTHER NEWS                    ▶ Expand  │
└────────────────────────────────────────────┘
```

### UI Component (Expanded)
```
┌────────────────────────────────────────────┐
│ 📰 OTHER NEWS                    ▼ Collapse│
├────────────────────────────────────────────┤
│                                            │
│ Today                                      │
│ • [35] SBV youth union conference          │
│ • [28] SEA Group partnership meeting       │
│                                            │
│ Yesterday                                  │
│ • [42] New circular on forex trading       │
│ • [30] Banking association meeting         │
│                                            │
│ Feb 3                                      │
│ • [38] Credit cooperation agreement        │
│                                            │
└────────────────────────────────────────────┘
```

### Data Source

| UI Element | Table | Query |
|------------|-------|-------|
| Events list | `events` | `WHERE display_section = 'other_news' ORDER BY published_at DESC` |
| Date grouping | `events` | Group by `DATE(published_at)` |
| Score | `events` | `current_score` |
| Title | `events` | `title` |

### API Endpoint
```
GET /api/events/other

Response:
{
  "groups": [
    {
      "date": "2026-02-05",
      "label": "Today",
      "events": [...]
    },
    {
      "date": "2026-02-04",
      "label": "Yesterday",
      "events": [...]
    }
  ]
}
```

---

## Footer Stats

### UI Component
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Sources: 1 | Events today: 5 | Key: 2 | Other: 3 | Investigations: 5       │
│ Last run: 14:30 | Status: ✅ Success                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Source

| UI Element | Table | Query |
|------------|-------|-------|
| Sources count | `run_history` | `sources_crawled` (latest) |
| Events today | `events` | `WHERE run_date = today()` |
| Key events | `events` | `WHERE display_section = 'key_events'` |
| Other news | `events` | `WHERE display_section = 'other_news'` |
| Investigations | `investigations` | `WHERE status IN ('open', 'updated')` |
| Last run time | `run_history` | `run_time` (latest) |
| Run status | `run_history` | `status` (latest) |

---

## Tab Navigation

### Tabs
| Tab | Content |
|-----|---------|
| 🇻🇳 Vietnam | Filter by `region = 'vietnam'` |
| 🌍 Global | Filter by `region = 'global'` |
| 📋 All News | Show all, no filter |
| 🔍 Investigations | Full investigations view |

### Filter Logic
```python
# Vietnam tab
events = await get_events(region="vietnam")
indicators = filter_by_category(["vietnam_monetary", "vietnam_forex", "vietnam_inflation"])

# Global tab
events = await get_events(region="global")
indicators = filter_by_category(["global_macro"])

# All News tab
events = await get_events()  # No filter

# Investigations tab
investigations = await get_investigations()
# Full page view with all investigations
```

---

## Summary: Table → UI Mapping

| Table | UI Components |
|-------|---------------|
| `indicators` | [A] Indicators Panel, Event Detail Modal (linked indicators) |
| `indicator_history` | Indicator Detail Modal (chart) |
| `events` | [B] Key Events, [E] Other News, Event Detail Modal |
| `causal_analyses` | Event Detail Modal (causal chain) |
| `topic_frequency` | Hot topic badges |
| `score_history` | (Analytics, not in main UI) |
| `investigations` | [D] Investigations Panel, Investigation Detail Modal |
| `investigation_evidence` | Investigation Detail Modal (timeline) |
| `predictions` | Event Detail Modal, Investigation Detail Modal |
| `run_history` | Footer stats |
| `calendar_events` | [C] Calendar Panel |
