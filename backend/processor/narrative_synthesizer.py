"""
Narrative Synthesizer - Generate trend narratives from signals.

This component synthesizes all active signals of a theme/trend into
a concise narrative using LLM. Triggered when:
- Signal is added to a theme
- Signal is verified (status changes)
- Manual refresh requested

Output: 3-5 sentence narrative summarizing the trend direction,
cause, implications, and timeline.
"""
from typing import Optional, List, Dict, Any

from loguru import logger

from llm import get_client, LLMClient
from prompts import PromptLoader


class NarrativeSynthesizer:
    """
    Generate narrative summaries for trends/themes.
    
    Uses active signals + related indicators to create
    a human-readable summary of what's happening.
    """
    
    def __init__(
        self,
        client: Optional[LLMClient] = None,
        max_retries: int = 2,
    ):
        """
        Initialize synthesizer.
        
        Args:
            client: LLM client instance (default GLM)
            max_retries: Retry attempts on failure
        """
        self.client = client or get_client()
        self.prompt_loader = PromptLoader()
        self.max_retries = max_retries
    
    def synthesize(
        self,
        theme_name: str,
        theme_description: str,
        first_seen: str,
        strength: float,
        signals: List[Dict[str, Any]],
        indicators: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Generate narrative for a theme based on its signals.
        
        Args:
            theme_name: Theme name
            theme_description: Theme description
            first_seen: When theme was first detected
            strength: Current theme strength
            signals: List of active signal dicts with keys:
                - prediction, direction, confidence, expires_at, reasoning
            indicators: List of related indicator dicts with keys:
                - indicator_id, name, current_value, unit
        
        Returns:
            Narrative string or None if generation fails
        """
        if not signals:
            logger.debug(f"No signals for theme '{theme_name}', skipping narrative")
            return None
        
        # Format signals section
        signals_section = self._format_signals(signals)
        
        # Format indicators section
        indicators_section = self._format_indicators(indicators)
        
        # Build prompt
        prompt = self.prompt_loader.format(
            "narrative_synthesis",
            theme_name=theme_name or "Unknown",
            theme_description=theme_description or "No description",
            first_seen=first_seen or "Unknown",
            strength=strength or 0,
            signals_count=len(signals),
            signals_section=signals_section,
            indicators_section=indicators_section,
        )
        
        # Call LLM
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.generate(
                    prompt=prompt,
                    system="You are a financial analyst summarizing market trends in Vietnamese.",
                    max_tokens=512,
                    temperature=0.7,
                )
                
                if response.success and response.content:
                    narrative = response.content.strip()
                    # Remove any markdown formatting or quotes
                    narrative = self._clean_narrative(narrative)
                    logger.info(f"Generated narrative for '{theme_name}' ({len(narrative)} chars)")
                    return narrative
                else:
                    logger.warning(f"LLM returned empty response for '{theme_name}'")
                    
            except Exception as e:
                logger.warning(f"Narrative synthesis attempt {attempt} failed: {e}")
                if attempt == self.max_retries:
                    logger.error(f"Narrative synthesis failed after {self.max_retries} attempts")
                    return None
        
        return None
    
    def _format_signals(self, signals: List[Dict[str, Any]]) -> str:
        """Format signals into detailed text for prompt.
        
        Includes target indicator, range, direction, confidence,
        expiry, and reasoning for each signal so the LLM can
        synthesize a richer narrative.
        """
        lines = []
        for i, sig in enumerate(signals, 1):
            confidence = sig.get('confidence', 'medium')
            direction = sig.get('direction', '')
            target_indicator = sig.get('target_indicator', '')
            
            # Header line: indicator + direction
            header = f"📊 **{target_indicator or 'General'}" 
            if direction:
                header += f" ({direction.upper()})"
            header += "**"
            lines.append(f"\n{i}. {header}")
            
            # Prediction text
            lines.append(f"   Prediction: {sig.get('prediction', 'No prediction')}")
            
            # Target range (if quantitative signal)
            range_low = sig.get('target_range_low')
            range_high = sig.get('target_range_high')
            if range_low is not None or range_high is not None:
                if range_low is not None and range_high is not None:
                    lines.append(f"   Target: {range_low} - {range_high}")
                elif range_low is not None:
                    lines.append(f"   Target: ≥ {range_low}")
                else:
                    lines.append(f"   Target: ≤ {range_high}")
            elif direction:
                lines.append(f"   Target: Direction only ({direction})")
            
            # Confidence and expiry
            expires = sig.get('expires_at', '')
            lines.append(f"   Confidence: {confidence.upper()}")
            if expires:
                lines.append(f"   Expires: {expires}")
            
            # Reasoning
            reasoning = sig.get('reasoning', '')
            if reasoning:
                lines.append(f"   Reasoning: {reasoning}")
            
            lines.append("   ---")
        
        return "\n".join(lines) if lines else "No active signals"
    
    def _format_indicators(self, indicators: List[Dict[str, Any]]) -> str:
        """Format indicators into readable text for prompt."""
        lines = []
        for ind in indicators:
            value = ind.get('current_value', 'N/A')
            unit = ind.get('unit', '')
            name = ind.get('name') or ind.get('indicator_id', 'Unknown')
            lines.append(f"- {name}: {value} {unit}".strip())
        
        return "\n".join(lines) if lines else "No related indicators"
    
    def _clean_narrative(self, text: str) -> str:
        """Remove markdown formatting and clean up narrative text."""
        # Remove markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        
        # Remove leading/trailing quotes
        text = text.strip('"\'')
        
        # Remove any "Output:" prefix
        if text.lower().startswith("output:"):
            text = text[7:].strip()
        
        return text.strip()
