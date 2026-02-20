"""
Classifier - Layer 1 News Classification

Filters news by market relevance and assigns categories.
This layer runs on all raw news before scoring.
"""
import json
import time
import re
from typing import Optional

from loguru import logger

from llm import get_client, LLMClient
from prompts import PromptLoader
from .models import ClassificationResult


class ClassificationError(Exception):
    """Raised when classification fails after all retries."""
    pass


class Classifier:
    """
    Layer 1: News Classification
    
    Filters news by market relevance and assigns categories.
    This layer runs on all raw news before scoring.
    
    Uses LLMClient interface (GLM by default).
    
    TODO: Implement batch classification to reduce LLM API calls
    Current: 73 events × 1 call = 73 calls (~4-6 mins best case, >1hr worst case)
    Target: Batch by token count (~15-20K tokens/batch), keep full content
    Approach:
    - Group items by estimated token count (not fixed item count)
    - Use JSON format with unique IDs for accurate result mapping
    - On batch failure: binary split and retry (not fallback to individual)
    - Preserve full content for accuracy (no truncation)
    """
    
    def __init__(
        self, 
        client: Optional[LLMClient] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        Initialize classifier.
        
        Args:
            client: LLM client instance (creates default GLM client if not provided)
            max_retries: Maximum number of retry attempts on failure
            retry_delay: Delay in seconds between retries
        """
        self.client = client or get_client()
        self.prompt_loader = PromptLoader()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    def classify(self, news_item: dict) -> ClassificationResult:
        """
        Classify a single news item with retry mechanism.
        
        Args:
            news_item: Dict with keys: title, content, source, date
            
        Returns:
            ClassificationResult with relevance, category, and linked indicators
            
        Raises:
            ClassificationError: If classification fails after all retries
        """
        prompt = self.prompt_loader.format(
            "classification",
            title=news_item.get('title', ''),
            content=news_item.get('content', news_item.get('summary', '')),
            source=news_item.get('source', ''),
            date=news_item.get('date', news_item.get('published_at', ''))
        )
        
        last_error = None
        last_raw_output = None
        original_task = f"Classify news: {news_item.get('title', '')[:100]}"
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # First attempt: use original prompt
                # Subsequent attempts: use fix_json prompt with previous output
                if attempt == 1 or not last_raw_output:
                    current_prompt = prompt
                else:
                    # Use fix_json prompt for retry
                    current_prompt = self.prompt_loader.format(
                        "fix_json",
                        original_task=original_task,
                        invalid_response=last_raw_output,
                        error_message=str(last_error),
                    )
                    logger.info(f"Using fix_json prompt for retry attempt {attempt}")
                
                response = self.client.generate(
                    prompt=current_prompt,
                    temperature=0.1,  # Low temp for consistent classification
                )
                
                raw_output = response.content
                last_raw_output = raw_output
                
                # Log raw output for debugging if empty
                if not raw_output or not raw_output.strip():
                    logger.warning(f"Empty response from LLM (attempt {attempt})")
                    raise json.JSONDecodeError("Empty response", "", 0)
                
                result = self._parse_response(raw_output)
                return result
                
            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(
                    f"Classification parse error (attempt {attempt}/{self.max_retries}): {e}"
                )
                if last_raw_output:
                    logger.debug(f"Raw output preview: {last_raw_output[:200]}...")
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                last_error = e
                logger.error(
                    f"LLM API error in classifier (attempt {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
        
        # All retries exhausted - raise exception
        title_preview = news_item.get('title', '')[:50]
        error_msg = f"Classification failed after {self.max_retries} attempts for: {title_preview}. Last error: {last_error}"
        logger.error(error_msg)
        raise ClassificationError(error_msg)
    
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
        """
        Parse LLM JSON response.
        
        Raises:
            json.JSONDecodeError: If response cannot be parsed as JSON
        """
        # Clean up response - remove markdown code blocks if present
        text = raw_output.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        # Try to fix common JSON issues
        # Fix trailing commas before closing brackets
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        
        # Parse JSON - let JSONDecodeError propagate for retry
        data = json.loads(text)
        
        return ClassificationResult(
            is_market_relevant=data.get('is_market_relevant', False),
            category=data.get('category') if data.get('category') != 'null' else None,
            linked_indicators=data.get('linked_indicators', []),
            reasoning=data.get('reasoning', ''),
            raw_output=raw_output
        )
