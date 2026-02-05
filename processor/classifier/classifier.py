"""
Classifier - Layer 1 News Classification

Filters news by market relevance and assigns categories.
This layer runs on all raw news before scoring.
"""
import json
from typing import Optional

from loguru import logger

from llm import get_client, LLMClient
from prompts import PromptLoader
from .models import ClassificationResult


class Classifier:
    """
    Layer 1: News Classification
    
    Filters news by market relevance and assigns categories.
    This layer runs on all raw news before scoring.
    
    Uses LLMClient interface (GLM by default).
    """
    
    def __init__(self, client: Optional[LLMClient] = None):
        """
        Initialize classifier.
        
        Args:
            client: LLM client instance (creates default GLM client if not provided)
        """
        self.client = client or get_client()
        self.prompt_loader = PromptLoader()
        
    def classify(self, news_item: dict) -> ClassificationResult:
        """
        Classify a single news item.
        
        Args:
            news_item: Dict with keys: title, content, source, date
            
        Returns:
            ClassificationResult with relevance, category, and linked indicators
        """
        prompt = self.prompt_loader.format(
            "classification",
            title=news_item.get('title', ''),
            content=news_item.get('content', news_item.get('summary', '')),
            source=news_item.get('source', ''),
            date=news_item.get('date', news_item.get('published_at', ''))
        )
        
        try:
            response = self.client.generate(
                prompt=prompt,
                temperature=0.1,  # Low temp for consistent classification
            )
            
            raw_output = response.content
            result = self._parse_response(raw_output)
            return result
            
        except Exception as e:
            logger.error(f"LLM API error in classifier: {e}")
            # Return as not relevant on error to avoid blocking pipeline
            return ClassificationResult(
                is_market_relevant=False,
                category=None,
                linked_indicators=[],
                reasoning=f"Classification error: {str(e)}",
                raw_output=""
            )
    
    def classify_batch(self, news_items: list[dict]) -> list[dict]:
        """
        Classify multiple news items.
        
        Args:
            news_items: List of news item dicts
            
        Returns:
            List of news items with classification results added
        """
        results = []
        
        for i, item in enumerate(news_items):
            logger.info(f"Classifying item {i+1}/{len(news_items)}: {item.get('title', '')[:50]}...")
            
            classification = self.classify(item)
            
            # Merge classification into item
            classified_item = {
                **item,
                **classification.to_dict()
            }
            results.append(classified_item)
        
        # Log stats
        relevant_count = sum(1 for r in results if r.get('is_market_relevant'))
        logger.info(f"Classification complete: {relevant_count}/{len(results)} items are market relevant")
        
        return results
    
    def filter_relevant(self, classified_items: list[dict]) -> list[dict]:
        """Filter to only market-relevant items."""
        return [item for item in classified_items if item.get('is_market_relevant')]
    
    def _parse_response(self, raw_output: str) -> ClassificationResult:
        """Parse LLM JSON response."""
        try:
            # Clean up response - remove markdown code blocks if present
            text = raw_output.strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            text = text.strip()
            
            data = json.loads(text)
            
            return ClassificationResult(
                is_market_relevant=data.get('is_market_relevant', False),
                category=data.get('category') if data.get('category') != 'null' else None,
                linked_indicators=data.get('linked_indicators', []),
                reasoning=data.get('reasoning', ''),
                raw_output=raw_output
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse classification response: {e}")
            logger.debug(f"Raw output: {raw_output}")
            
            # Try to extract is_market_relevant from text
            is_relevant = '"is_market_relevant": true' in raw_output.lower()
            
            return ClassificationResult(
                is_market_relevant=is_relevant,
                category=None,
                linked_indicators=[],
                reasoning="Parse error - extracted from raw",
                raw_output=raw_output
            )
