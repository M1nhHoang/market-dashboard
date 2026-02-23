"""
Vietcombank Mappings

Currency code to metric_id mappings, display names, etc.
"""

# Key currencies to track as individual indicators on dashboard
KEY_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CNY", "AUD",
    "SGD", "KRW", "THB", "CAD", "CHF", "HKD",
}

# Currency code → metric_id and display info
# Each currency produces up to 3 metrics: buy, transfer, sell
CURRENCY_MAP = {
    "USD": {
        "metric_id_prefix": "usd_vnd_vcb",
        "name": "USD/VND",
        "name_vi": "Tỷ giá USD/VND (VCB)",
    },
    "EUR": {
        "metric_id_prefix": "eur_vnd_vcb",
        "name": "EUR/VND",
        "name_vi": "Tỷ giá EUR/VND (VCB)",
    },
    "GBP": {
        "metric_id_prefix": "gbp_vnd_vcb",
        "name": "GBP/VND",
        "name_vi": "Tỷ giá GBP/VND (VCB)",
    },
    "JPY": {
        "metric_id_prefix": "jpy_vnd_vcb",
        "name": "JPY/VND",
        "name_vi": "Tỷ giá JPY/VND (VCB)",
    },
    "CNY": {
        "metric_id_prefix": "cny_vnd_vcb",
        "name": "CNY/VND",
        "name_vi": "Tỷ giá CNY/VND (VCB)",
    },
    "AUD": {
        "metric_id_prefix": "aud_vnd_vcb",
        "name": "AUD/VND",
        "name_vi": "Tỷ giá AUD/VND (VCB)",
    },
    "SGD": {
        "metric_id_prefix": "sgd_vnd_vcb",
        "name": "SGD/VND",
        "name_vi": "Tỷ giá SGD/VND (VCB)",
    },
    "KRW": {
        "metric_id_prefix": "krw_vnd_vcb",
        "name": "KRW/VND",
        "name_vi": "Tỷ giá KRW/VND (VCB)",
    },
    "THB": {
        "metric_id_prefix": "thb_vnd_vcb",
        "name": "THB/VND",
        "name_vi": "Tỷ giá THB/VND (VCB)",
    },
    "CAD": {
        "metric_id_prefix": "cad_vnd_vcb",
        "name": "CAD/VND",
        "name_vi": "Tỷ giá CAD/VND (VCB)",
    },
    "CHF": {
        "metric_id_prefix": "chf_vnd_vcb",
        "name": "CHF/VND",
        "name_vi": "Tỷ giá CHF/VND (VCB)",
    },
    "HKD": {
        "metric_id_prefix": "hkd_vnd_vcb",
        "name": "HKD/VND",
        "name_vi": "Tỷ giá HKD/VND (VCB)",
    },
}

# Rate type suffixes and display names
RATE_TYPES = {
    "buy": {
        "suffix": "_buy",
        "name_suffix": " Buy (Cash)",
        "name_vi_suffix": " Mua tiền mặt",
    },
    "transfer": {
        "suffix": "_transfer",
        "name_suffix": " Buy (Transfer)",
        "name_vi_suffix": " Mua chuyển khoản",
    },
    "sell": {
        "suffix": "_sell",
        "name_suffix": " Sell",
        "name_vi_suffix": " Bán",
    },
}

# Indicator defaults for dashboard display
INDICATOR_DEFAULTS = {
    "usd_vnd_vcb_sell": {
        "name": "USD/VND Sell (VCB)",
        "name_vi": "Tỷ giá bán USD/VND (VCB)",
        "unit": "VND",
        "category": "vietnam_forex",
        "subcategory": "exchange_rate",
        "source": "Vietcombank",
    },
    "eur_vnd_vcb_sell": {
        "name": "EUR/VND Sell (VCB)",
        "name_vi": "Tỷ giá bán EUR/VND (VCB)",
        "unit": "VND",
        "category": "vietnam_forex",
        "subcategory": "exchange_rate",
        "source": "Vietcombank",
    },
    "jpy_vnd_vcb_sell": {
        "name": "JPY/VND Sell (VCB)",
        "name_vi": "Tỷ giá bán JPY/VND (VCB)",
        "unit": "VND",
        "category": "vietnam_forex",
        "subcategory": "exchange_rate",
        "source": "Vietcombank",
    },
    "cny_vnd_vcb_sell": {
        "name": "CNY/VND Sell (VCB)",
        "name_vi": "Tỷ giá bán CNY/VND (VCB)",
        "unit": "VND",
        "category": "vietnam_forex",
        "subcategory": "exchange_rate",
        "source": "Vietcombank",
    },
}
