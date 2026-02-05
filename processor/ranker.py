"""
Layer 3: Ranker - Apply time decay and boost factors, assign display sections.

This is the third layer in the 3-layer LLM pipeline:
1. CLASSIFIER - Filter and categorize news
2. SCORER - Score and analyze relevant news
3. RANKER (this) - Rank and decay all active events

The Ranker:
- Applies time decay based on event age
- Applies boost factors (follow-ups, hot topics)
- Assigns display sections (key_events, other_news, archive)
- Identifies hot topics (3+ occurrences in 7 days)

This layer can run without LLM for basic decay/ranking,
or with LLM for more sophisticated hot topic detection.
"""
import json
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

import anthropic
from loguru import logger

from config import settings


@dataclass
class RankingResult:
    """Result of ranking an event."""
    event_id: str
    age_days: int
    original_score: float
    decay_factor: float
    boost_factor: float
    final_score: float
    display_section: str
    hot_topic: Optional[str]
    
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "age_days": self.age_days,
            "original_score": self.original_score,
            "decay_factor": self.decay_factor,
            "boost_factor": self.boost_factor,
            "final_score": self.final_score,
            "display_section": self.display_section,
            "hot_topic": self.hot_topic
        }


# ============================================
# DECAY CONFIGURATION
# ============================================

DECAY_SCHEDULE = {
    # age_days: decay_factor
    0: 1.0,      # Today: 100%
    1: 0.95,     # 1 day: 95%
    2: 0.90,     # 2 days: 90%
    3: 0.85,     # 3 days: 85%
    4: 0.75,     # 4-5 days: 75%
    5: 0.75,
    6: 0.70,     # 6-7 days: 70%
    7: 0.70,
    8: 0.55,     # 8-14 days: 55%
    14: 0.55,
    15: 0.35,    # 15-30 days: 35%
    30: 0.35,
    31: 0.0      # 30+ days: Archive
}

# Boost factors
BOOST_FOLLOW_UP = 1.20      # +20% for follow-up to investigation
BOOST_HOT_TOPIC = 1.15      # +15% for hot topic
BOOST_MULTI_INDICATOR = 1.10  # +10% for connecting 2+ indicators

# Display thresholds
THRESHOLD_KEY_EVENTS = 50    # final_score >= 50 AND has linked_indicators
THRESHOLD_OTHER_NEWS = 20    # final_score >= 20
MAX_KEY_EVENTS = 15          # Maximum in key_events section


def get_decay_factor(age_days: int) -> float:
    """Get decay factor for given age in days."""
    if age_days >= 31:
        return 0.0  # Archive
    
    # Find the closest age bracket
    for day in sorted(DECAY_SCHEDULE.keys(), reverse=True):
        if age_days >= day:
            return DECAY_SCHEDULE[day]
    
    return 1.0


def calculate_boost_factor(
    event: dict,
    open_investigation_ids: list[str] = None,
    hot_topics: list[str] = None
) -> float:
    """Calculate boost factor for an event."""
    boost = 1.0
    open_investigation_ids = open_investigation_ids or []
    hot_topics = hot_topics or []
    
    # Follow-up boost
    if event.get('is_follow_up') and event.get('follows_up_on') in open_investigation_ids:
        boost *= BOOST_FOLLOW_UP
    
    # Hot topic boost
    if event.get('hot_topic') and event.get('hot_topic') in hot_topics:
        boost *= BOOST_HOT_TOPIC
    
    # Multi-indicator boost
    linked = event.get('linked_indicators', [])
    if isinstance(linked, str):
        linked = json.loads(linked) if linked else []
    if len(linked) >= 2:
        boost *= BOOST_MULTI_INDICATOR
    
    return boost


def determine_display_section(
    final_score: float,
    linked_indicators: list,
    age_days: int,
    is_market_relevant: bool = True
) -> str:
    """Determine which display section an event belongs to."""
    if age_days >= 31:
        return 'archive'
    
    if not is_market_relevant:
        return 'archive'
    
    if final_score < THRESHOLD_OTHER_NEWS:
        return 'archive'
    
    has_indicators = bool(linked_indicators)
    if final_score >= THRESHOLD_KEY_EVENTS and has_indicators:
        return 'key_events'
    
    return 'other_news'


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


# ============================================
# INVESTIGATION REVIEWER (Can run separately)
# ============================================

from prompts import PromptLoader


class InvestigationReviewer:
    """Reviews investigations and updates their status."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.LLM_MODEL
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.prompt_loader = PromptLoader()
    
    def review(
        self,
        open_investigations: list[dict],
        todays_events: list[dict]
    ) -> dict:
        """
        Review investigations with today's events.
        
        Args:
            open_investigations: List of open investigation dicts
            todays_events: List of today's scored events
            
        Returns:
            Dict with investigation updates
        """
        if not open_investigations:
            return {"investigation_updates": []}
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        prompt = self.prompt_loader.format(
            "investigation_review",
            today=today,
            open_investigations=json.dumps(open_investigations, ensure_ascii=False, indent=2),
            todays_events=json.dumps(
                [{"id": e.get("id"), "title": e.get("title"), "category": e.get("category"), 
                  "base_score": e.get("base_score"), "causal_analysis": e.get("causal_analysis")}
                 for e in todays_events],
                ensure_ascii=False, indent=2
            )
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw_output = response.content[0].text
            return self._parse_response(raw_output)
            
        except Exception as e:
            logger.error(f"Investigation review failed: {e}")
            return {"investigation_updates": [], "error": str(e)}
    
    def _parse_response(self, raw_output: str) -> dict:
        """Parse investigation review response."""
        try:
            text = raw_output.strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            text = text.strip()
            
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse investigation review: {e}")
            return {"investigation_updates": [], "parse_error": str(e)}
