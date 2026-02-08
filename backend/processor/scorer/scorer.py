"""
Scorer - Layer 2 News Scoring

Scores market-relevant news and performs causal analysis.
Generates signals (predictions) and links to themes.
"""
import json
from pathlib import Path

from loguru import logger

from config import settings
from llm import get_client, LLMClient
from prompts import PromptLoader
from .models import ScoringResult, SignalOutput, ThemeLink


class Scorer:
    """
    Layer 2: News Scoring
    
    Scores market-relevant news and performs causal analysis.
    Generates signals (predictions) and links to themes.
    """
    
    def __init__(
        self, 
        client: LLMClient = None,
        templates_path: Path = None
    ):
        """
        Initialize scorer.
        
        Args:
            client: LLM client instance (creates default if not provided)
            templates_path: Path to causal templates JSON file
        """
        self.client = client or get_client()
        self.prompt_loader = PromptLoader()
        
        # Load causal templates
        self.templates_path = templates_path or (settings.BASE_DIR / "templates" / "causal_templates.json")
        self.templates = self._load_templates()
        
    def _load_templates(self) -> dict:
        """Load causal templates from JSON file."""
        try:
            with open(self.templates_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Templates file not found: {self.templates_path}")
            return {"templates": []}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse templates: {e}")
            return {"templates": []}
    
    def score(
        self,
        news_item: dict,
        previous_context_summary: str = "",
        active_signals: list[dict] = None,
        active_themes: list[dict] = None,
        lookback_days: int = 7
    ) -> ScoringResult:
        """
        Score a single classified news item.
        
        Args:
            news_item: Dict with classification results (from Layer 1)
            previous_context_summary: Summary of previous analysis context
            active_signals: List of active signal dicts (pending predictions)
            active_themes: List of active theme dicts
            lookback_days: Days of context
            
        Returns:
            ScoringResult with score breakdown, signal output, and theme link
        """
        active_signals = active_signals or []
        active_themes = active_themes or []
        
        prompt = self.prompt_loader.format(
            "scoring",
            title=news_item.get('title', ''),
            content=news_item.get('content', news_item.get('summary', '')),
            category=news_item.get('category', 'unknown'),
            linked_indicators=json.dumps(news_item.get('linked_indicators', [])),
            source=news_item.get('source', ''),
            date=news_item.get('date', news_item.get('published_at', '')),
            lookback_days=lookback_days,
            previous_context_summary=previous_context_summary or "No previous context available.",
            active_signals=json.dumps(active_signals, ensure_ascii=False, indent=2) if active_signals else "No active signals.",
            active_themes=json.dumps(active_themes, ensure_ascii=False, indent=2) if active_themes else "No active themes.",
            causal_templates=json.dumps(self.templates, ensure_ascii=False, indent=2)
        )
        
        try:
            response = self.client.generate(
                prompt=prompt,
                temperature=0.3,
            )
            
            raw_output = response.content
            result = self._parse_response(raw_output)
            return result
            
        except Exception as e:
            logger.exception(f"LLM error in scorer: {e}")
            return self._error_result(str(e))
    
    def score_batch(
        self,
        news_items: list[dict],
        previous_context_summary: str = "",
        active_signals: list[dict] = None,
        active_themes: list[dict] = None,
        lookback_days: int = 7
    ) -> list[dict]:
        """
        Score multiple news items.
        
        Args:
            news_items: List of classified news items (from Layer 1)
            previous_context_summary: Summary of previous context
            active_signals: List of active signals
            active_themes: List of active themes
            lookback_days: Days of context
            
        Returns:
            List of news items with scoring results added
        """
        results = []
        active_signals = active_signals or []
        active_themes = active_themes or []
        
        for i, item in enumerate(news_items):
            logger.info(f"Scoring item {i+1}/{len(news_items)}: {item.get('title', '')[:50]}...")
            
            scoring = self.score(
                item, 
                previous_context_summary, 
                active_signals,
                active_themes,
                lookback_days
            )
            
            # Merge scoring into item
            scored_item = {
                **item,
                **scoring.to_dict()
            }
            results.append(scored_item)
        
        # Log stats
        avg_score = sum(r.get('base_score', 0) for r in results) / len(results) if results else 0
        high_score_count = sum(1 for r in results if r.get('base_score', 0) >= 60)
        logger.info(f"Scoring complete: avg={avg_score:.1f}, high_score={high_score_count}/{len(results)}")
        
        return results
    
    def _parse_response(self, raw_output: str) -> ScoringResult:
        """Parse LLM JSON response."""
        try:
            # Clean up response
            text = raw_output.strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            text = text.strip()
            
            data = json.loads(text)
            
            # Parse signal output
            signal_data = data.get('signal_output', {})
            signal_output = SignalOutput(
                create_signal=signal_data.get('create_signal', False),
                prediction=signal_data.get('prediction'),
                target_indicator=signal_data.get('target_indicator'),
                direction=signal_data.get('direction'),
                target_range_low=signal_data.get('target_range_low'),
                target_range_high=signal_data.get('target_range_high'),
                confidence=signal_data.get('confidence', 'medium'),
                timeframe_days=signal_data.get('timeframe_days'),
                reasoning=signal_data.get('reasoning'),
            )
            
            # Parse theme link
            theme_data = data.get('theme_link', {})
            theme_link = ThemeLink(
                existing_theme_id=theme_data.get('existing_theme_id'),
                create_new_theme=theme_data.get('create_new_theme', False),
                new_theme=theme_data.get('new_theme'),
            )
            
            return ScoringResult(
                base_score=data.get('base_score', 50),
                score_factors=data.get('score_factors', {}),
                causal_analysis=data.get('causal_analysis', {}),
                signal_output=signal_output,
                theme_link=theme_link,
                raw_output=raw_output
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse scoring response: {e}")
            logger.debug(f"Raw output: {raw_output}")
            return self._error_result(f"JSON parse error: {e}")
    
    def _error_result(self, error_msg: str) -> ScoringResult:
        """Return a default result on error."""
        return ScoringResult(
            base_score=30,  # Default to low-medium score
            score_factors={
                "direct_indicator_impact": 10,
                "policy_significance": 5,
                "market_breadth": 5,
                "novelty": 5,
                "source_authority": 5
            },
            causal_analysis={
                "matched_template_id": None,
                "chain": [],
                "confidence": "uncertain",
                "reasoning": f"Scoring error: {error_msg}"
            },
            signal_output=SignalOutput(create_signal=False),
            theme_link=ThemeLink(create_new_theme=False),
            raw_output="",
            parse_error=error_msg
        )
