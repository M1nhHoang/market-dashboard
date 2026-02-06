"""
Calendar Crawler - Economic calendar events

⚠️ PLACEHOLDER - Needs actual data source from user

Expected data:
- Economic event date/time
- Country
- Event name
- Importance level
- Forecast/Previous/Actual values
"""
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

import httpx
from loguru import logger

from .base_crawler import BaseCrawler, CrawlResult


@dataclass
class CalendarEvent:
    """Economic calendar event structure."""
    date: str
    time: Optional[str]
    event_name: str
    country: str
    importance: str  # 'high', 'medium', 'low'
    forecast: Optional[str]
    previous: Optional[str]
    actual: Optional[str]
    
    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "time": self.time,
            "event_name": self.event_name,
            "country": self.country,
            "importance": self.importance,
            "forecast": self.forecast,
            "previous": self.previous,
            "actual": self.actual
        }


class CalendarCrawler(BaseCrawler):
    """
    Crawler for economic calendar events.
    
    TODO: User needs to provide:
    - Data source (API or website)
    - cURL command if API
    - Scraping instructions if website
    """
    
    def __init__(self, data_dir: Path):
        super().__init__("calendar", data_dir)
        
        # TODO: Replace with actual endpoint from user
        self.base_url = "https://api.example.com/calendar"
        self.headers = {
            "User-Agent": "MarketIntelligence/1.0"
        }
        
    async def fetch(self) -> CrawlResult:
        """
        Fetch economic calendar events.
        
        ⚠️ PLACEHOLDER IMPLEMENTATION
        """
        logger.warning("[Calendar] Using placeholder - need actual data source")
        
        return CrawlResult(
            source="calendar",
            crawled_at=datetime.now(),
            success=False,
            data=[],
            error="Placeholder: Need actual data source from user"
        )
    
    async def fetch_week(self) -> list[CalendarEvent]:
        """
        Fetch this week's economic events.
        
        Expected structure (to be confirmed with user):
        [
            {
                "date": "2026-02-05",
                "time": "14:30",
                "event": "US Non-Farm Payrolls",
                "country": "US",
                "importance": "high",
                "forecast": "180K",
                "previous": "256K"
            }
        ]
        """
        # TODO: Implement based on actual API response
        return []
    
    async def fetch_vietnam_events(self) -> list[CalendarEvent]:
        """
        Fetch Vietnam-specific economic events.
        
        Expected events:
        - CPI release
        - GDP release
        - Trade balance
        - SBV meetings
        """
        # TODO: Implement based on actual data source
        return []


# ============================================================
# INSTRUCTIONS FOR USER
# ============================================================
"""
To complete this crawler, please provide:

1. Economic Calendar Source:
   Common options:
   - Investing.com calendar API/feed
   - ForexFactory calendar
   - TradingEconomics
   - Custom API
   
2. Provide:
   - cURL command to fetch calendar data
   - Sample response JSON
   - Any authentication needed
   
3. Specify which events to track:
   - Vietnam events (CPI, GDP, trade, etc.)
   - US events (Fed, NFP, CPI, etc.)
   - China events (PMI, trade, etc.)
   - Other relevant events

Example format:
```
curl -X GET 'https://calendar.example.com/api/events' \
  -H 'Authorization: Bearer xxx' \
  -d 'from=2026-02-01&to=2026-02-07&countries=US,VN,CN'

Response:
{
  "events": [
    {
      "date": "2026-02-05",
      "time": "14:30",
      "event": "US Non-Farm Payrolls",
      ...
    }
  ]
}
```
"""
