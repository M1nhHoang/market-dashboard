"""
Investigation Reviewer - Review and update investigation statuses.

This component reviews open investigations against new events
and updates their status (open, updated, resolved, stale, escalated).
"""
import json
from datetime import datetime

import anthropic
from loguru import logger

from config import settings
from prompts import PromptLoader


class InvestigationReviewer:
    """
    Reviews investigations and updates their status.
    
    Uses LLM to analyze whether new events provide evidence
    for or against open investigations.
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize reviewer.
        
        Args:
            api_key: Anthropic API key (uses settings if not provided)
            model: LLM model name (uses settings if not provided)
        """
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
