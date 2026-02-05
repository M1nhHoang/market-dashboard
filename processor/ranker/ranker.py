"""
Ranker - Layer 3 Event Ranking

Applies decay, boosts, and determines display sections.
Runs on ALL active events, not just today's.
"""
import json
from datetime import datetime
from typing import Optional

import anthropic
from loguru import logger

from config import settings
from .models import RankingResult
from .config import (
    MAX_KEY_EVENTS,
    get_decay_factor,
    calculate_boost_factor,
    determine_display_section,
)


class Ranker:
    """
    Layer 3: Event Ranking
    
    Applies decay, boosts, and determines display sections.
    Runs on ALL active events, not just today's.
    """
    
    def __init__(self, use_llm_for_topics: bool = False):
        """
        Initialize ranker.
        
        Args:
            use_llm_for_topics: Whether to use LLM for hot topic detection
                               (if False, uses simple frequency counting)
        """
        self.use_llm = use_llm_for_topics
        if use_llm_for_topics:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = settings.LLM_MODEL
    
    def rank_event(
        self,
        event: dict,
        today: datetime = None,
        open_investigation_ids: list[str] = None,
        hot_topics: list[str] = None
    ) -> RankingResult:
        """
        Rank a single event.
        
        Args:
            event: Event dict with base_score and metadata
            today: Reference date (defaults to now)
            open_investigation_ids: List of open investigation IDs
            hot_topics: List of hot topic names
            
        Returns:
            RankingResult with final score and display section
        """
        today = today or datetime.now()
        
        # Calculate age
        published_at = event.get('published_at') or event.get('created_at')
        if isinstance(published_at, str):
            try:
                published_dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except:
                published_dt = today  # Assume today if can't parse
        else:
            published_dt = today
        
        age_days = (today - published_dt.replace(tzinfo=None)).days
        if age_days < 0:
            age_days = 0
        
        # Get base score
        base_score = event.get('base_score') or event.get('current_score') or 50
        
        # Calculate factors
        decay = get_decay_factor(age_days)
        boost = calculate_boost_factor(event, open_investigation_ids, hot_topics)
        
        # Calculate final score
        final_score = base_score * decay * boost
        
        # Parse linked indicators
        linked = event.get('linked_indicators', [])
        if isinstance(linked, str):
            linked = json.loads(linked) if linked else []
        
        # Determine display section
        display_section = determine_display_section(
            final_score=final_score,
            linked_indicators=linked,
            age_days=age_days,
            is_market_relevant=event.get('is_market_relevant', True)
        )
        
        return RankingResult(
            event_id=event.get('id', ''),
            age_days=age_days,
            original_score=base_score,
            decay_factor=decay,
            boost_factor=boost,
            final_score=round(final_score, 2),
            display_section=display_section,
            hot_topic=event.get('hot_topic')
        )
    
    def rank_all_events(
        self,
        events: list[dict],
        open_investigation_ids: list[str] = None,
        hot_topics: list[str] = None
    ) -> dict:
        """
        Rank all active events.
        
        Args:
            events: List of event dicts
            open_investigation_ids: List of open investigation IDs
            hot_topics: List of hot topic names
            
        Returns:
            Dict with rankings and summary
        """
        today = datetime.now()
        rankings = []
        
        for event in events:
            result = self.rank_event(
                event, 
                today,
                open_investigation_ids,
                hot_topics
            )
            rankings.append(result.to_dict())
        
        # Sort by final score
        rankings.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Apply max key_events limit
        key_count = 0
        for r in rankings:
            if r['display_section'] == 'key_events':
                key_count += 1
                if key_count > MAX_KEY_EVENTS:
                    r['display_section'] = 'other_news'
        
        # Calculate summary
        section_counts = {
            'key_events': sum(1 for r in rankings if r['display_section'] == 'key_events'),
            'other_news': sum(1 for r in rankings if r['display_section'] == 'other_news'),
            'archive': sum(1 for r in rankings if r['display_section'] == 'archive')
        }
        
        logger.info(f"Ranking complete: key={section_counts['key_events']}, "
                   f"other={section_counts['other_news']}, archive={section_counts['archive']}")
        
        return {
            "rankings": rankings,
            "section_summary": section_counts,
            "ranked_at": today.isoformat()
        }
    
    def detect_hot_topics(
        self,
        events: list[dict],
        days: int = 7,
        min_occurrences: int = 3
    ) -> list[dict]:
        """
        Detect hot topics from recent events.
        Simple frequency-based approach (no LLM needed).
        
        Args:
            events: List of event dicts from last N days
            days: Lookback period
            min_occurrences: Minimum occurrences to be "hot"
            
        Returns:
            List of hot topic dicts
        """
        # Extract categories and keywords
        topic_counts = {}
        
        for event in events:
            # Use category as topic
            category = event.get('category')
            if category and category != 'internal':
                topic_counts[category] = topic_counts.get(category, 0) + 1
            
            # Extract from causal_analysis if available
            causal = event.get('causal_analysis', {})
            if isinstance(causal, str):
                try:
                    causal = json.loads(causal)
                except:
                    causal = {}
            
            template_id = causal.get('matched_template_id')
            if template_id:
                topic_counts[template_id] = topic_counts.get(template_id, 0) + 1
        
        # Filter to hot topics
        hot_topics = []
        for topic, count in topic_counts.items():
            if count >= min_occurrences:
                hot_topics.append({
                    "topic": topic,
                    "count_7d": count,
                    "is_hot": True
                })
        
        hot_topics.sort(key=lambda x: x['count_7d'], reverse=True)
        
        return hot_topics
