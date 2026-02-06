# Database Schema Documentation

## Overview

Market Intelligence Dashboard sử dụng SQLite với SQLAlchemy ORM để lưu trữ dữ liệu thị trường, tin tức, và phân tích nhân quả.

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE SCHEMA                                    │
└─────────────────────────────────────────────────────────────────────────────┘

                           ┌─────────────────┐
                           │   INDICATORS    │
                           ├─────────────────┤
                           │ id (PK)         │
                           │ name            │
                           │ category        │
                           │ value           │
                           │ change          │
                           │ updated_at      │
                           └────────┬────────┘
                                    │
                                    │ 1:N
                                    ▼
                           ┌─────────────────┐
                           │INDICATOR_HISTORY│
                           ├─────────────────┤
                           │ id (PK)         │
                           │ indicator_id(FK)│───────────────────┐
                           │ value           │                   │
                           │ date            │                   │
                           │ recorded_at     │                   │
                           └─────────────────┘                   │
                                                                 │
┌─────────────────┐        ┌─────────────────┐                   │
│ TOPIC_FREQUENCY │        │     EVENTS      │                   │
├─────────────────┤        ├─────────────────┤                   │
│ id (PK)         │        │ id (PK)         │                   │
│ topic           │        │ title           │                   │
│ occurrence_count│        │ category        │                   │
│ is_hot          │        │ linked_indicators│──────────────────┘
│ related_events  │◄───────│ base_score      │     (JSON array)
└─────────────────┘        │ current_score   │
                           │ display_section │
                           │ hash (UNIQUE)   │
                           └───────┬─────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          │ 1:N                    │ 1:N                    │ 1:N
          ▼                        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│CAUSAL_ANALYSES  │     │  SCORE_HISTORY  │     │   PREDICTIONS   │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ event_id (FK)   │     │ event_id (FK)   │     │ source_event_id │
│ template_id     │     │ score           │     │ investigation_id│
│ chain_steps     │     │ display_section │     │ prediction      │
│ confidence      │     │ recorded_at     │     │ confidence      │
│ needs_investig. │     └─────────────────┘     │ check_by_date   │
└─────────────────┘                             └────────┬────────┘
                                                         │
                                                         │ N:1
                                                         ▼
                                              ┌─────────────────┐
                                              │ INVESTIGATIONS  │
                                              ├─────────────────┤
                                              │ id (PK)         │
                                              │ question        │
                                              │ status          │
                                              │ priority        │
                                              │ evidence_count  │
                                              │ resolution      │
                                              └────────┬────────┘
                                                       │
                                                       │ 1:N
                                                       ▼
                                           ┌─────────────────────┐
                                           │INVESTIGATION_EVIDENCE│
                                           ├─────────────────────┤
                                           │ id (PK)             │
                                           │ investigation_id(FK)│
                                           │ event_id (FK)       │
                                           │ evidence_type       │
                                           │ summary             │
                                           └─────────────────────┘


┌─────────────────┐        ┌─────────────────┐
│   RUN_HISTORY   │        │ CALENDAR_EVENTS │
├─────────────────┤        ├─────────────────┤
│ id (PK)         │        │ id (PK)         │
│ run_date        │        │ date            │
│ run_time        │        │ event_name      │
│ sources_crawled │        │ country         │
│ raw_data_path   │        │ importance      │
│ crawl_stats     │        │ forecast        │
│ events_extracted│        │ actual          │
│ status          │        └─────────────────┘
└─────────────────┘        UNIQUE(date, event_name, country)
```

---

## Table Specifications

### 1. indicators

Lưu trữ giá trị hiện tại của các chỉ số thị trường.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | VD: `interbank_on`, `usd_vnd_central` |
| name | TEXT | NOT NULL | Tên tiếng Anh |
| name_vi | TEXT | | Tên tiếng Việt |
| category | TEXT | | `vietnam_monetary`, `vietnam_forex`, etc. |
| subcategory | TEXT | | Phân nhóm trong UI |
| value | REAL | | Giá trị hiện tại |
| unit | TEXT | | Đơn vị (%, tỷ VND, etc.) |
| change | REAL | | Thay đổi tuyệt đối |
| change_pct | REAL | | Thay đổi % |
| trend | TEXT | | `up`, `down`, `stable` |
| source | TEXT | | Nguồn dữ liệu |
| source_url | TEXT | | URL nguồn |
| updated_at | TIMESTAMP | | Thời điểm cập nhật |

**Indexes:**
- PRIMARY KEY on `id`

---

### 2. indicator_history

Lịch sử giá trị indicator theo thời gian.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | UUID |
| indicator_id | TEXT | FK → indicators.id (CASCADE) | Reference tới indicator |
| value | REAL | NOT NULL | Giá trị tại thời điểm |
| previous_value | REAL | | Giá trị trước đó |
| change | REAL | | Thay đổi |
| change_pct | REAL | | Thay đổi % |
| volume | REAL | | Khối lượng giao dịch (interbank) |
| date | DATE | NOT NULL | Ngày ghi nhận |
| recorded_at | TIMESTAMP | | Thời điểm ghi nhận |
| source | TEXT | | Nguồn dữ liệu |

**Indexes:**
- `idx_indicator_history_lookup` on `(indicator_id, date DESC)`
- UNIQUE on `(indicator_id, date, value)`

---

### 3. events

Tin tức và sự kiện đã được phân tích.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | UUID |
| title | TEXT | NOT NULL | Tiêu đề tin |
| summary | TEXT | | Tóm tắt |
| content | TEXT | | Nội dung đầy đủ |
| source | TEXT | | Nguồn (SBV, VnEconomy, etc.) |
| source_url | TEXT | | URL gốc |
| is_market_relevant | BOOLEAN | DEFAULT TRUE | Có liên quan thị trường |
| category | TEXT | | `monetary`, `fiscal`, `banking`, etc. |
| region | TEXT | | `vietnam`, `global` |
| linked_indicators | JSON | | Array các indicator IDs |
| base_score | INTEGER | | Điểm gốc 1-100 từ LLM |
| score_factors | JSON | | Chi tiết điểm |
| current_score | REAL | | Điểm sau decay & boost |
| decay_factor | REAL | DEFAULT 1.0 | Hệ số suy giảm |
| boost_factor | REAL | DEFAULT 1.0 | Hệ số tăng cường |
| display_section | TEXT | | `key_events`, `other_news`, `archive` |
| hot_topic | TEXT | | Tên topic nếu là hot topic |
| is_follow_up | BOOLEAN | DEFAULT FALSE | Là tin follow-up |
| follows_up_on | TEXT | | ID event/investigation theo dõi |
| published_at | TIMESTAMP | | Thời gian đăng |
| created_at | TIMESTAMP | | Thời gian tạo record |
| run_date | DATE | | Ngày xử lý |
| last_ranked_at | TIMESTAMP | | Lần rank cuối |
| hash | TEXT | UNIQUE | Hash nội dung (dedup) |

**Indexes:**
- `idx_events_display` on `(display_section, current_score DESC)`
- `idx_events_date` on `published_at DESC`
- `idx_events_hash` on `hash`

---

### 4. causal_analyses

Phân tích chuỗi nhân quả cho mỗi event.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | UUID |
| event_id | TEXT | FK → events.id (CASCADE) | Event liên quan |
| template_id | TEXT | | ID template trong causal_templates.json |
| chain_steps | JSON | | Array các bước nhân quả |
| confidence | TEXT | | `verified`, `likely`, `uncertain` |
| needs_investigation | JSON | | Array các câu hỏi cần điều tra |
| affected_indicators | JSON | | Array indicator IDs bị ảnh hưởng |
| impact_on_vn | TEXT | | Tác động lên VN |
| reasoning | TEXT | | Lý giải |
| created_at | TIMESTAMP | | |

---

### 5. topic_frequency

Theo dõi tần suất xuất hiện của các topic.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | UUID |
| topic | TEXT | NOT NULL | Tên topic |
| category | TEXT | | Phân loại |
| occurrence_count | INTEGER | DEFAULT 1 | Số lần xuất hiện |
| first_seen | DATE | | Lần đầu thấy |
| last_seen | DATE | | Lần cuối thấy |
| related_event_ids | JSON | | Array event IDs |
| is_hot | BOOLEAN | DEFAULT FALSE | Hot nếu 3+ lần/7 ngày |

---

### 6. score_history

Lịch sử điểm số của events (để phân tích).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | UUID |
| event_id | TEXT | FK → events.id (CASCADE) | |
| score | REAL | | Điểm tại thời điểm |
| decay_factor | REAL | | |
| boost_factor | REAL | | |
| display_section | TEXT | | |
| recorded_at | TIMESTAMP | | |

---

### 7. investigations

Các câu hỏi đang được theo dõi/điều tra.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | UUID |
| question | TEXT | NOT NULL | Câu hỏi điều tra |
| context | TEXT | | Bối cảnh |
| source_event_id | TEXT | | Event khởi tạo investigation |
| status | TEXT | DEFAULT 'open' | `open`, `updated`, `resolved`, `stale`, `escalated` |
| priority | TEXT | DEFAULT 'medium' | `high`, `medium`, `low` |
| evidence_count | INTEGER | DEFAULT 0 | Số evidence |
| evidence_summary | TEXT | | Tóm tắt evidence |
| resolution | TEXT | | Kết luận nếu resolved |
| resolution_confidence | TEXT | | Độ tin cậy kết luận |
| resolved_by_event_id | TEXT | | Event giải quyết |
| created_at | TIMESTAMP | | |
| updated_at | TIMESTAMP | | |
| last_evidence_at | TIMESTAMP | | |
| resolved_at | TIMESTAMP | | |
| related_indicators | JSON | | Array indicator IDs |
| related_templates | JSON | | Array template IDs |

---

### 8. investigation_evidence

Evidence cho investigations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | UUID |
| investigation_id | TEXT | FK → investigations.id (CASCADE) | |
| event_id | TEXT | FK → events.id (SET NULL) | Event là evidence |
| evidence_type | TEXT | | `supports`, `contradicts`, `neutral` |
| summary | TEXT | | Tóm tắt |
| added_at | TIMESTAMP | | |

---

### 9. predictions

Dự đoán từ phân tích.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | UUID |
| source_event_id | TEXT | FK → events.id (SET NULL) | Event gốc |
| investigation_id | TEXT | FK → investigations.id (SET NULL) | Investigation liên quan |
| prediction | TEXT | NOT NULL | Nội dung dự đoán |
| confidence | TEXT | | `high`, `medium`, `low` |
| check_by_date | DATE | | Ngày kiểm tra |
| verification_indicator | TEXT | | Indicator để verify |
| status | TEXT | DEFAULT 'pending' | `pending`, `verified`, `failed` |
| actual_result | TEXT | | Kết quả thực tế |
| verified_at | TIMESTAMP | | |
| created_at | TIMESTAMP | | |

**Indexes:**
- `idx_predictions_investigation` on `investigation_id`

---

### 10. run_history

Lịch sử các lần chạy pipeline.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | UUID |
| run_date | DATE | | Ngày chạy |
| run_time | TIMESTAMP | | Thời điểm chạy |
| raw_data_path | TEXT | | Đường dẫn file raw data (new) |
| sources_crawled | JSON | | Danh sách sources đã crawl (new) |
| crawl_stats | JSON | | Stats cho từng source (new) |
| news_count | INTEGER | | Số tin tổng |
| events_extracted | INTEGER | | Số events trích xuất |
| events_key | INTEGER | | Số key events |
| events_other | INTEGER | | Số other news |
| investigations_opened | INTEGER | | Investigations mới |
| investigations_updated | INTEGER | | Investigations cập nhật |
| investigations_resolved | INTEGER | | Investigations đã giải quyết |
| summary | TEXT | | Tóm tắt |
| status | TEXT | | `success`, `partial`, `failed` |

---

### 11. calendar_events

Lịch kinh tế sắp tới.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | UUID |
| date | DATE | | Ngày sự kiện |
| time | TIME | | Giờ |
| event_name | TEXT | | Tên sự kiện |
| country | TEXT | | Quốc gia |
| importance | TEXT | | `high`, `medium`, `low` |
| forecast | TEXT | | Dự báo |
| previous | TEXT | | Giá trị kỳ trước |
| actual | TEXT | | Giá trị thực tế |
| created_at | TIMESTAMP | | |

**Constraints:**
- UNIQUE on `(date, event_name, country)` — tránh duplicate khi re-crawl

**Indexes:**
- `idx_calendar_country` on `country`

---

## Foreign Key Relationships

| From Table | Column | To Table | On Delete |
|------------|--------|----------|-----------|
| indicator_history | indicator_id | indicators | CASCADE |
| causal_analyses | event_id | events | CASCADE |
| score_history | event_id | events | CASCADE |
| investigation_evidence | investigation_id | investigations | CASCADE |
| investigation_evidence | event_id | events | SET NULL |
| predictions | source_event_id | events | SET NULL |
| predictions | investigation_id | investigations | SET NULL |

---

## Enums & Constants

### Event Categories
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

### Investigation Statuses
```python
INVESTIGATION_STATUSES = [
    "open",       # Đang theo dõi
    "updated",    # Có evidence mới
    "resolved",   # Đã có câu trả lời
    "stale",      # Không có update > 14 ngày
    "escalated"   # Cần human review
]
```

### Display Sections
```python
DISPLAY_SECTIONS = [
    "key_events",   # Tin quan trọng (top, sorted by score)
    "other_news",   # Tin khác (collapsed, sorted by date)
    "archive"       # Tin cũ > 30 ngày
]
```
