"""
Indicator Mappings Constants

Defines all indicator IDs, groupings, and mappings from source data.
This file serves as the central reference for indicator definitions.

NOTE: These mappings will be extended as more data sources are added.
Currently supports:
- SBV (State Bank of Vietnam) data sources

TODO: Add mappings for future data sources:
- Global market crawlers (Fed, ECB, BOJ)
- Vietnam stock market indicators (VN-Index, HNX)
- Commodity prices (oil, metals)
- External API integrations
"""
from enum import Enum
from typing import Dict, List, Any


# ============================================
# INDICATOR ID PATTERNS
# ============================================
# Naming convention: {source}_{type}_{variant}
# Examples:
#   - interbank_on (interbank overnight rate)
#   - usd_vnd_central (central exchange rate)
#   - cpi_mom (CPI month-over-month)
#   - omo_net_daily (daily OMO net injection)


# ============================================
# INDICATOR GROUPS (for UI display)
# ============================================

INDICATOR_GROUPS: Dict[str, Dict[str, Any]] = {
    "vietnam_monetary": {
        "display_name": "🏦 Monetary Policy",
        "display_name_vi": "🏦 Chính sách tiền tệ",
        "description": "SBV policy rates, interbank rates, OMO operations",
        "indicators": [
            "omo_net_daily",
            "rediscount_rate",
            "refinancing_rate",
            "interbank_on",
            "interbank_1w",
            "interbank_2w",
            "interbank_1m",
            "interbank_3m",
            "interbank_6m",
            "interbank_9m",
        ],
    },
    "vietnam_forex": {
        "display_name": "💱 Exchange Rate",
        "display_name_vi": "💱 Tỷ giá hối đoái",
        "description": "USD/VND and other currency rates",
        "indicators": [
            "usd_vnd_central",
            # TODO: Add more forex indicators when available
            # "eur_vnd", "jpy_vnd", "cny_vnd"
        ],
    },
    "vietnam_inflation": {
        "display_name": "📈 Inflation",
        "display_name_vi": "📈 Lạm phát",
        "description": "CPI and inflation metrics",
        "indicators": [
            "cpi_mom",
            "cpi_yoy",
            "cpi_ytd",
            "core_inflation",
        ],
    },
    "vietnam_commodity": {
        "display_name": "🪙 Commodity",
        "display_name_vi": "🪙 Hàng hóa",
        "description": "Gold and other commodity prices",
        "indicators": [
            "gold_sjc",
            # TODO: Add more commodity indicators
            # "gold_pnj", "gold_doji"
        ],
    },
    # TODO: Add these groups when global crawler is implemented
    # "global_monetary": {
    #     "display_name": "🌍 Global Central Banks",
    #     "display_name_vi": "🌍 NHTW Thế giới",
    #     "description": "Fed, ECB, BOJ, PBOC rates",
    #     "indicators": ["fed_rate", "ecb_rate", "boj_rate", "pboc_rate"],
    # },
    # "global_forex": {
    #     "display_name": "💵 Global Forex",
    #     "display_name_vi": "💵 Ngoại hối Thế giới",
    #     "description": "DXY, major pairs",
    #     "indicators": ["dxy", "eurusd", "usdjpy", "usdcny"],
    # },
    # "global_bonds": {
    #     "display_name": "📊 Bond Yields",
    #     "display_name_vi": "📊 Lợi suất Trái phiếu",
    #     "description": "Government bond yields",
    #     "indicators": ["us10y", "us2y", "de10y", "jp10y"],
    # },
    # "global_commodity": {
    #     "display_name": "🛢️ Global Commodities",
    #     "display_name_vi": "🛢️ Hàng hóa Thế giới",
    #     "description": "Oil, metals, agriculture",
    #     "indicators": ["brent_oil", "wti_oil", "gold_spot", "silver_spot"],
    # },
}


# ============================================
# SBV DATA MAPPINGS
# ============================================

# Interbank rates: Map Vietnamese term names to indicator IDs
INTERBANK_TERM_MAP: Dict[str, str] = {
    "Qua đêm": "interbank_on",
    "1 Tuần": "interbank_1w",
    "2 Tuần": "interbank_2w",
    "1 Tháng": "interbank_1m",
    "3 Tháng": "interbank_3m",
    "6 Tháng": "interbank_6m",
    "9 Tháng": "interbank_9m",
    # Alternative spellings found in data
    "Qua Đêm": "interbank_on",
    "ON": "interbank_on",
    "1W": "interbank_1w",
    "2W": "interbank_2w",
    "1M": "interbank_1m",
    "3M": "interbank_3m",
    "6M": "interbank_6m",
    "9M": "interbank_9m",
}

# Policy rates: Map rate type names to indicator definitions
POLICY_RATE_MAP: Dict[str, Dict[str, str]] = {
    "tái chiết khấu": {
        "indicator_id": "rediscount_rate",
        "name": "Rediscount Rate",
        "name_vi": "Lãi suất tái chiết khấu",
    },
    "tái cấp vốn": {
        "indicator_id": "refinancing_rate",
        "name": "Refinancing Rate",
        "name_vi": "Lãi suất tái cấp vốn",
    },
    # TODO: Add more policy rate types when discovered
    # "lãi suất cơ bản": {
    #     "indicator_id": "base_rate",
    #     "name": "Base Rate",
    #     "name_vi": "Lãi suất cơ bản",
    # },
}

# Gold prices: Map source/type combinations to indicator definitions
GOLD_PRICE_MAP: Dict[str, Dict[str, str]] = {
    "SJC": {
        "indicator_id": "gold_sjc",
        "name": "SJC Gold Price",
        "name_vi": "Giá vàng SJC",
    },
    # TODO: Add more gold sources when available
    # "DOJI": {
    #     "indicator_id": "gold_doji",
    #     "name": "DOJI Gold Price",
    #     "name_vi": "Giá vàng DOJI",
    # },
    # "PNJ": {
    #     "indicator_id": "gold_pnj",
    #     "name": "PNJ Gold Price",
    #     "name_vi": "Giá vàng PNJ",
    # },
}

# CPI indicators: Defines all CPI-related indicator IDs
CPI_INDICATOR_MAP: Dict[str, Dict[str, str]] = {
    "mom": {
        "indicator_id": "cpi_mom",
        "name": "CPI Month-over-Month",
        "name_vi": "CPI so với tháng trước",
        "description": "Monthly CPI change vs previous month",
    },
    "yoy": {
        "indicator_id": "cpi_yoy",
        "name": "CPI Year-over-Year",
        "name_vi": "CPI so với cùng kỳ năm trước",
        "description": "Monthly CPI change vs same month last year",
    },
    "ytd": {
        "indicator_id": "cpi_ytd",
        "name": "CPI Year-to-Date",
        "name_vi": "CPI bình quân từ đầu năm",
        "description": "Average CPI change from start of year",
    },
    "core": {
        "indicator_id": "core_inflation",
        "name": "Core Inflation",
        "name_vi": "Lạm phát cơ bản",
        "description": "CPI excluding food and energy",
    },
}

# OMO indicators: Open Market Operations
OMO_INDICATOR_MAP: Dict[str, Dict[str, str]] = {
    "net_daily": {
        "indicator_id": "omo_net_daily",
        "name": "OMO Net Daily",
        "name_vi": "OMO ròng trong ngày",
        "description": "Net liquidity injection (inject - withdraw)",
    },
    "inject": {
        "indicator_id": "omo_inject_daily",
        "name": "OMO Daily Injection",
        "name_vi": "OMO bơm trong ngày",
        "description": "Reverse repo (Mua kỳ hạn)",
    },
    "withdraw": {
        "indicator_id": "omo_withdraw_daily",
        "name": "OMO Daily Withdrawal",
        "name_vi": "OMO hút trong ngày",
        "description": "Repo (Bán kỳ hạn)",
    },
    # TODO: Add weekly/monthly aggregates
    # "net_weekly": {...},
    # "net_mtd": {...},
}


# ============================================
# EVENT CATEGORIES
# ============================================

EVENT_CATEGORIES: Dict[str, str] = {
    "monetary": "Monetary policy (OMO, interest rates, liquidity)",
    "fiscal": "Fiscal policy (public investment, budget, tax)",
    "banking": "Banking sector (NPL, credit, bank financials)",
    "economic": "Macroeconomic (GDP, CPI, import/export)",
    "geopolitical": "Geopolitical (trade war, sanctions)",
    "corporate": "Corporate news (non-bank companies)",
    "regulatory": "New regulations, legal changes",
    "internal": "Internal activities (SBV conferences, appointments)",
}

# Vietnamese category names for UI
EVENT_CATEGORIES_VI: Dict[str, str] = {
    "monetary": "Chính sách tiền tệ (OMO, lãi suất, thanh khoản)",
    "fiscal": "Chính sách tài khóa (đầu tư công, ngân sách, thuế)",
    "banking": "Ngân hàng (nợ xấu, tín dụng, tài chính)",
    "economic": "Vĩ mô (GDP, CPI, xuất nhập khẩu)",
    "geopolitical": "Địa chính trị (chiến tranh thương mại, cấm vận)",
    "corporate": "Doanh nghiệp (không phải ngân hàng)",
    "regulatory": "Quy định mới, thay đổi pháp luật",
    "internal": "Hoạt động nội bộ (hội nghị, bổ nhiệm)",
}


# ============================================
# STATUS & DISPLAY CONSTANTS
# ============================================

class DisplaySection(str, Enum):
    """Event display sections in UI."""
    KEY_EVENTS = "key_events"
    OTHER_NEWS = "other_news"
    ARCHIVE = "archive"


class PriorityLevel(str, Enum):
    """Priority levels for investigations."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InvestigationStatus(str, Enum):
    """Investigation status states."""
    OPEN = "open"
    UPDATED = "updated"
    RESOLVED = "resolved"
    STALE = "stale"
    ESCALATED = "escalated"


class PredictionStatus(str, Enum):
    """Prediction verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class ConfidenceLevel(str, Enum):
    """Confidence levels for analyses."""
    VERIFIED = "verified"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"


class EvidenceType(str, Enum):
    """Types of evidence for investigations."""
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


# Dict versions for backward compatibility
DISPLAY_SECTIONS = {s.value: s.value for s in DisplaySection}
PRIORITY_LEVELS = {p.value: p.value for p in PriorityLevel}
INVESTIGATION_STATUS = {s.value: s.value for s in InvestigationStatus}
PREDICTION_STATUS = {s.value: s.value for s in PredictionStatus}
CONFIDENCE_LEVELS = {c.value: c.value for c in ConfidenceLevel}


# ============================================
# INDICATOR METADATA DEFAULTS
# ============================================

INDICATOR_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "interbank_on": {
        "name": "Interbank Overnight",
        "name_vi": "Lãi suất liên ngân hàng Qua đêm",
        "unit": "% năm",
        "category": "vietnam_monetary",
        "subcategory": "interbank",
        "source": "SBV",
    },
    "interbank_1w": {
        "name": "Interbank 1 Week",
        "name_vi": "Lãi suất liên ngân hàng 1 Tuần",
        "unit": "% năm",
        "category": "vietnam_monetary",
        "subcategory": "interbank",
        "source": "SBV",
    },
    "usd_vnd_central": {
        "name": "USD/VND Central Rate",
        "name_vi": "Tỷ giá trung tâm USD/VND",
        "unit": "VND",
        "category": "vietnam_forex",
        "subcategory": "exchange_rate",
        "source": "SBV",
    },
    "gold_sjc": {
        "name": "SJC Gold Price",
        "name_vi": "Giá vàng SJC",
        "unit": "VND/lượng",
        "category": "vietnam_commodity",
        "subcategory": "gold",
        "source": "SBV/SJC",
    },
    "cpi_mom": {
        "name": "CPI Month-over-Month",
        "name_vi": "CPI so với tháng trước",
        "unit": "%",
        "category": "vietnam_inflation",
        "subcategory": "cpi",
        "source": "SBV/GSO",
    },
    "cpi_yoy": {
        "name": "CPI Year-over-Year",
        "name_vi": "CPI so với cùng kỳ",
        "unit": "%",
        "category": "vietnam_inflation",
        "subcategory": "cpi",
        "source": "SBV/GSO",
    },
    "omo_net_daily": {
        "name": "OMO Net Daily",
        "name_vi": "OMO ròng trong ngày",
        "unit": "Tỷ đồng",
        "category": "vietnam_monetary",
        "subcategory": "omo",
        "source": "SBV",
    },
    "rediscount_rate": {
        "name": "Rediscount Rate",
        "name_vi": "Lãi suất tái chiết khấu",
        "unit": "%",
        "category": "vietnam_monetary",
        "subcategory": "policy_rate",
        "source": "SBV",
    },
    "refinancing_rate": {
        "name": "Refinancing Rate",
        "name_vi": "Lãi suất tái cấp vốn",
        "unit": "%",
        "category": "vietnam_monetary",
        "subcategory": "policy_rate",
        "source": "SBV",
    },
    # TODO: Add defaults for global indicators
    # "fed_rate": {
    #     "name": "Fed Funds Rate",
    #     "name_vi": "Lãi suất Fed",
    #     "unit": "%",
    #     "category": "global_monetary",
    #     "subcategory": "central_bank",
    #     "source": "Federal Reserve",
    # },
}


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_indicator_id(source_type: str, raw_value: str) -> str | None:
    """
    Get indicator ID from source type and raw value.
    
    Args:
        source_type: Type of data source ('interbank', 'policy_rate', etc.)
        raw_value: Raw value from crawler (e.g., 'Qua đêm', 'tái chiết khấu')
        
    Returns:
        Indicator ID or None if not found
    """
    if source_type == "interbank":
        return INTERBANK_TERM_MAP.get(raw_value)
    elif source_type == "policy_rate":
        for key, mapping in POLICY_RATE_MAP.items():
            if key.lower() in raw_value.lower():
                return mapping["indicator_id"]
    elif source_type == "gold":
        for key, mapping in GOLD_PRICE_MAP.items():
            if key in raw_value:
                return mapping["indicator_id"]
    return None


def get_indicator_metadata(indicator_id: str) -> Dict[str, Any] | None:
    """
    Get default metadata for an indicator.
    
    Args:
        indicator_id: The indicator ID
        
    Returns:
        Dict with name, name_vi, unit, category, subcategory, source
    """
    return INDICATOR_DEFAULTS.get(indicator_id)


def get_indicators_by_category(category: str) -> List[str]:
    """
    Get all indicator IDs for a category.
    
    Args:
        category: Category name (e.g., 'vietnam_monetary')
        
    Returns:
        List of indicator IDs
    """
    group = INDICATOR_GROUPS.get(category, {})
    return group.get("indicators", [])
