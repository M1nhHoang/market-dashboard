# Market Intelligence Dashboard

Hệ thống phân tích tin tức tài chính vĩ mô Việt Nam và thế giới, sử dụng LLM để giải thích **TẠI SAO** các chỉ số biến động.

## 🎯 Tính năng chính

- **Thu thập tin tức** từ nhiều nguồn (RSS, API)
- **Phân tích LLM** với context từ các lần chạy trước (context continuity)
- **Causal chain mapping** - liên kết sự kiện với chuỗi nhân quả
- **Investigation tracking** - theo dõi các điểm cần điều tra
- **Dashboard** hiển thị insights

## 📁 Cấu trúc Project

```
market-intelligence/
├── crawlers/               # Data collectors
│   ├── base_crawler.py     # Abstract base class
│   ├── sbv_crawler.py      # Vietnam central bank data
│   ├── news_crawler.py     # RSS feeds
│   ├── calendar_crawler.py # Economic calendar
│   └── global_crawler.py   # Global market data
├── processor/              # LLM processing
│   ├── llm_processor.py    # Main processor
│   ├── context_builder.py  # Build previous context
│   ├── prompts.py          # LLM prompts
│   └── output_parser.py    # Parse LLM output
├── templates/
│   └── causal_templates.json  # Predefined causal chains
├── api/                    # FastAPI backend
│   ├── main.py
│   └── routes.py
├── frontend/               # React app (to be created)
├── data/                   # Data storage
│   ├── raw/               # Raw crawled data
│   ├── processed/         # LLM output
│   └── market.db          # SQLite database
├── config.py              # Configuration
├── database.py            # Database schema
├── scheduler.py           # Automated jobs
└── requirements.txt
```

## 🚀 Setup

### 1. Tạo Virtual Environment

```bash
cd market-intelligence
python -m venv venv
venv\Scripts\activate  # Windows
# hoặc: source venv/bin/activate  # Linux/Mac
```

### 2. Cài đặt Dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu hình Environment

```bash
cp .env.example .env
# Sửa .env và thêm ANTHROPIC_API_KEY
```

### 4. Khởi tạo Database

```bash
python database.py
```

### 5. Chạy API Server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 6. Chạy Scheduler (optional)

```bash
python scheduler.py
```

## 📊 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/indicators` | List indicators |
| `GET /api/events` | List events |
| `GET /api/events/today` | Today's events |
| `GET /api/investigations` | Open investigations |
| `GET /api/topics/trending` | Trending topics |
| `GET /api/calendar` | Economic calendar |
| `GET /api/runs` | Processing history |
| `POST /api/refresh` | Trigger manual refresh |

## ⚠️ TODO: Data Sources

Các crawler hiện tại là **placeholder**. Cần cung cấp data sources:

### SBV Crawler
- [ ] OMO operations API/source
- [ ] Exchange rate API
- [ ] Policy rate source

### News Crawler
- [ ] VnEconomy RSS feed
- [ ] CafeF RSS feed
- [ ] VnExpress Economy RSS

### Calendar Crawler
- [ ] Economic calendar API

### Global Crawler
- [ ] DXY data source
- [ ] US10Y yield source
- [ ] Commodities (Gold, Oil) API

## 🔧 Development

```bash
# Run tests
pytest

# Format code
black .

# Type check
mypy .
```

## 📝 License

MIT
