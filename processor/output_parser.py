"""
Output Parser - Parse and validate LLM output
"""
import json
import re
from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime

from loguru import logger


@dataclass
class ParsedAnalysis:
    """Parsed and validated LLM analysis output."""
    analysis_date: str
    run_id: str
    events: list[dict]
    investigation_updates: list[dict]
    new_investigations: list[dict]
    recurring_topic_flags: list[dict]
    indicator_alerts: list[dict]
    predictions: list[dict]
    daily_summary: str
    raw_output: str
    parse_errors: list[str]
    
    @property
    def is_valid(self) -> bool:
        return len(self.parse_errors) == 0


class OutputParser:
    """Parse and validate LLM JSON output."""
    
    # Required fields and their types
    REQUIRED_FIELDS = {
        "analysis_date": str,
        "run_id": str,
        "events": list,
        "daily_summary": str
    }
    
    OPTIONAL_FIELDS = {
        "investigation_updates": list,
        "new_investigations": list,
        "recurring_topic_flags": list,
        "indicator_alerts": list,
        "predictions": list
    }
    
    EVENT_REQUIRED_FIELDS = {
        "id": str,
        "title": str,
        "category": str,
        "region": str,
        "impact": str
    }
    
    def parse(self, llm_output: str) -> ParsedAnalysis:
        """
        Parse LLM output string to structured data.
        
        Handles:
        - JSON extraction from markdown code blocks
        - Field validation
        - Type checking
        - Default values for optional fields
        """
        errors = []
        raw_output = llm_output
        
        # Step 1: Extract JSON from output
        json_str = self._extract_json(llm_output)
        
        if not json_str:
            errors.append("Could not extract JSON from LLM output")
            return self._empty_result(raw_output, errors)
        
        # Step 2: Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            errors.append(f"JSON parse error: {str(e)}")
            # Try to fix common issues
            fixed_json = self._try_fix_json(json_str)
            if fixed_json:
                try:
                    data = json.loads(fixed_json)
                    errors = []  # Clear error if fix worked
                except:
                    return self._empty_result(raw_output, errors)
            else:
                return self._empty_result(raw_output, errors)
        
        # Step 3: Validate required fields
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(data[field], expected_type):
                errors.append(f"Invalid type for {field}: expected {expected_type.__name__}")
        
        # Step 4: Validate events
        events = data.get("events", [])
        validated_events = []
        for i, event in enumerate(events):
            event_errors = self._validate_event(event, i)
            if event_errors:
                errors.extend(event_errors)
            else:
                validated_events.append(event)
        
        # Step 5: Build result
        return ParsedAnalysis(
            analysis_date=data.get("analysis_date", datetime.now().strftime("%Y-%m-%d")),
            run_id=data.get("run_id", f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            events=validated_events,
            investigation_updates=data.get("investigation_updates", []),
            new_investigations=data.get("new_investigations", []),
            recurring_topic_flags=data.get("recurring_topic_flags", []),
            indicator_alerts=data.get("indicator_alerts", []),
            predictions=data.get("predictions", []),
            daily_summary=data.get("daily_summary", ""),
            raw_output=raw_output,
            parse_errors=errors
        )
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text, handling markdown code blocks."""
        # Try to find JSON in code block
        code_block_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
        matches = re.findall(code_block_pattern, text)
        
        if matches:
            # Return the longest match (likely the main JSON)
            return max(matches, key=len).strip()
        
        # Try to find raw JSON (starts with {)
        json_pattern = r'\{[\s\S]*\}'
        matches = re.findall(json_pattern, text)
        
        if matches:
            return max(matches, key=len).strip()
        
        return None
    
    def _try_fix_json(self, json_str: str) -> Optional[str]:
        """Try to fix common JSON issues."""
        fixed = json_str
        
        # Remove trailing commas
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)
        
        # Fix unescaped quotes in strings (basic attempt)
        # This is tricky and may not always work
        
        return fixed
    
    def _validate_event(self, event: dict, index: int) -> list[str]:
        """Validate a single event object."""
        errors = []
        
        for field, expected_type in self.EVENT_REQUIRED_FIELDS.items():
            if field not in event:
                errors.append(f"Event {index}: missing required field '{field}'")
            elif not isinstance(event[field], expected_type):
                errors.append(f"Event {index}: invalid type for '{field}'")
        
        # Validate enum fields
        if event.get("category") not in ["monetary", "fiscal", "banking", "economic", "geopolitical", None]:
            errors.append(f"Event {index}: invalid category '{event.get('category')}'")
            
        if event.get("region") not in ["vietnam", "global", None]:
            errors.append(f"Event {index}: invalid region '{event.get('region')}'")
            
        if event.get("impact") not in ["high", "medium", "low", None]:
            errors.append(f"Event {index}: invalid impact '{event.get('impact')}'")
        
        return errors
    
    def _empty_result(self, raw_output: str, errors: list[str]) -> ParsedAnalysis:
        """Return empty result with errors."""
        return ParsedAnalysis(
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            run_id=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            events=[],
            investigation_updates=[],
            new_investigations=[],
            recurring_topic_flags=[],
            indicator_alerts=[],
            predictions=[],
            daily_summary="",
            raw_output=raw_output,
            parse_errors=errors
        )
