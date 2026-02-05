"""
SBV Data Mappings

All mappings specific to SBV (State Bank of Vietnam) data source.
Includes indicator ID mappings, metadata defaults, and categories.
"""
from typing import Dict, Any


# ============================================
# INTERBANK RATE MAPPINGS
# ============================================

# Map Vietnamese term names to indicator IDs
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


# ============================================
# POLICY RATE MAPPINGS
# ============================================

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
}


# ============================================
# GOLD PRICE MAPPINGS
# ============================================

GOLD_PRICE_MAP: Dict[str, Dict[str, str]] = {
    "SJC": {
        "indicator_id": "gold_sjc",
        "name": "SJC Gold Price",
        "name_vi": "Giá vàng SJC",
    },
}


# ============================================
# CPI MAPPINGS
# ============================================

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


# ============================================
# OMO MAPPINGS
# ============================================

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
}


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
        "indicators": ["usd_vnd_central"],
    },
    "vietnam_inflation": {
        "display_name": "📈 Inflation",
        "display_name_vi": "📈 Lạm phát",
        "description": "CPI and inflation metrics",
        "indicators": ["cpi_mom", "cpi_yoy", "cpi_ytd", "core_inflation"],
    },
    "vietnam_commodity": {
        "display_name": "🪙 Commodity",
        "display_name_vi": "🪙 Hàng hóa",
        "description": "Gold and other commodity prices",
        "indicators": ["gold_sjc"],
    },
}


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
    "interbank_2w": {
        "name": "Interbank 2 Weeks",
        "name_vi": "Lãi suất liên ngân hàng 2 Tuần",
        "unit": "% năm",
        "category": "vietnam_monetary",
        "subcategory": "interbank",
        "source": "SBV",
    },
    "interbank_1m": {
        "name": "Interbank 1 Month",
        "name_vi": "Lãi suất liên ngân hàng 1 Tháng",
        "unit": "% năm",
        "category": "vietnam_monetary",
        "subcategory": "interbank",
        "source": "SBV",
    },
    "interbank_3m": {
        "name": "Interbank 3 Months",
        "name_vi": "Lãi suất liên ngân hàng 3 Tháng",
        "unit": "% năm",
        "category": "vietnam_monetary",
        "subcategory": "interbank",
        "source": "SBV",
    },
    "interbank_6m": {
        "name": "Interbank 6 Months",
        "name_vi": "Lãi suất liên ngân hàng 6 Tháng",
        "unit": "% năm",
        "category": "vietnam_monetary",
        "subcategory": "interbank",
        "source": "SBV",
    },
    "interbank_9m": {
        "name": "Interbank 9 Months",
        "name_vi": "Lãi suất liên ngân hàng 9 Tháng",
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
    "cpi_ytd": {
        "name": "CPI Year-to-Date",
        "name_vi": "CPI bình quân từ đầu năm",
        "unit": "%",
        "category": "vietnam_inflation",
        "subcategory": "cpi",
        "source": "SBV/GSO",
    },
    "core_inflation": {
        "name": "Core Inflation",
        "name_vi": "Lạm phát cơ bản",
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
    "omo_inject_daily": {
        "name": "OMO Daily Injection",
        "name_vi": "OMO bơm trong ngày",
        "unit": "Tỷ đồng",
        "category": "vietnam_monetary",
        "subcategory": "omo",
        "source": "SBV",
    },
    "omo_withdraw_daily": {
        "name": "OMO Daily Withdrawal",
        "name_vi": "OMO hút trong ngày",
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
}


# ============================================
# EVENT CATEGORIES (SBV-specific)
# ============================================

EVENT_CATEGORIES: Dict[str, str] = {
    "monetary": "Monetary policy (OMO, interest rates, liquidity)",
    "fiscal": "Fiscal policy (public investment, budget, tax)",
    "banking": "Banking sector (NPL, credit, bank financials)",
    "economic": "Macroeconomic (GDP, CPI, import/export)",
    "regulatory": "New regulations, legal changes",
    "internal": "Internal activities (SBV conferences, appointments)",
}

EVENT_CATEGORIES_VI: Dict[str, str] = {
    "monetary": "Chính sách tiền tệ (OMO, lãi suất, thanh khoản)",
    "fiscal": "Chính sách tài khóa (đầu tư công, ngân sách, thuế)",
    "banking": "Ngân hàng (nợ xấu, tín dụng, tài chính)",
    "economic": "Vĩ mô (GDP, CPI, xuất nhập khẩu)",
    "regulatory": "Quy định mới, thay đổi pháp luật",
    "internal": "Hoạt động nội bộ (hội nghị, bổ nhiệm)",
}
