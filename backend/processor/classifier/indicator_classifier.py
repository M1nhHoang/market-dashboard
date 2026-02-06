"""
Indicator Data Classifier - Rule-based classification (No LLM needed)

Separates raw crawler data into:
- Indicator updates (structured data)
- News items (for LLM classification)
"""
from loguru import logger


def classify_indicator_data(raw_data: list[dict]) -> dict:
    """
    Classify raw SBV data into indicator updates vs news.
    This doesn't need LLM - pure rule-based.
    
    Args:
        raw_data: List of raw data items from crawler
        
    Returns:
        {
            "indicators": [...],  # Indicator data to update
            "news": [...]         # News items to classify with LLM
        }
    """
    indicators = []
    news = []
    
    # Known indicator types from SBV crawler
    INDICATOR_TYPES = {
        'exchange_rate',
        'gold_price',
        'policy_rate',
        'interbank_rate',
        'cpi',
        'omo'
    }
    
    for item in raw_data:
        item_type = item.get('type', '')
        
        if item_type == 'metadata':
            continue  # Skip crawl stats
        
        if item_type in INDICATOR_TYPES:
            indicators.append(item)
        elif item_type == 'news':
            news.append(item)
        else:
            # Unknown type - treat as news if it has a title
            if item.get('title'):
                news.append(item)
    
    logger.info(f"Classified raw data: {len(indicators)} indicators, {len(news)} news items")
    
    return {
        "indicators": indicators,
        "news": news
    }
