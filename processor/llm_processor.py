"""
LLM Processor - Main processing logic using Claude API
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic
from loguru import logger

from config import settings
from prompts import PromptLoader
from .context_builder import ContextBuilder
from .output_parser import OutputParser, ParsedAnalysis


class LLMProcessor:
    """
    Main LLM processor for analyzing news and generating insights.
    
    Uses two-prompt strategy:
    1. Context summary prompt - compress previous context
    2. Main analysis prompt - analyze today's news with context
    """
    
    def __init__(
        self, 
        db_path: Path,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.LLM_MODEL
        self.context_builder = ContextBuilder(db_path)
        self.output_parser = OutputParser()
        self.prompt_loader = PromptLoader()
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Load causal templates
        self.templates = self._load_templates()
        
    def _load_templates(self) -> dict:
        """Load causal templates from JSON file."""
        template_path = settings.BASE_DIR / "templates" / "causal_templates.json"
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Templates file not found: {template_path}")
            return {"templates": []}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse templates: {e}")
            return {"templates": []}
    
    async def run_analysis(
        self,
        news_articles: list[dict],
        indicators: list[dict],
        lookback_days: int = 7
    ) -> ParsedAnalysis:
        """
        Run the complete analysis pipeline.
        
        Args:
            news_articles: List of news article dicts
            indicators: List of current indicator values
            lookback_days: Days to look back for context
            
        Returns:
            ParsedAnalysis object with results
        """
        analysis_date = datetime.now().strftime("%Y-%m-%d")
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info(f"Starting analysis run {run_id}")
        
        # Step 1: Build previous context
        logger.info("Building previous context...")
        previous_context = self.context_builder.build_previous_context(lookback_days)
        previous_context_text = self.context_builder.format_for_prompt(previous_context)
        
        # Step 2: Get context summary from LLM (first call)
        logger.info("Generating context summary...")
        context_summary = await self._get_context_summary(
            previous_context_text,
            lookback_days
        )
        
        # Step 3: Get open investigations
        open_investigations = previous_context.get("open_investigations", [])
        investigations_text = json.dumps(open_investigations, ensure_ascii=False, indent=2)
        
        # Step 4: Run main analysis (second call)
        logger.info("Running main analysis...")
        main_prompt = self.prompt_loader.format(
            "main_analysis",
            previous_context_summary=context_summary,
            news_articles=json.dumps(news_articles, ensure_ascii=False, indent=2),
            current_indicators=json.dumps(indicators, ensure_ascii=False, indent=2),
            causal_templates=json.dumps(self.templates, ensure_ascii=False, indent=2),
            open_investigations=investigations_text,
            analysis_date=analysis_date,
            run_id=run_id
        )
        
        analysis_output = await self._call_llm(main_prompt)
        
        # Step 5: Parse and validate output
        logger.info("Parsing LLM output...")
        result = self.output_parser.parse(analysis_output)
        
        if result.is_valid:
            logger.info(f"Analysis complete: {len(result.events)} events extracted")
        else:
            logger.warning(f"Analysis has errors: {result.parse_errors}")
        
        return result
    
    async def _get_context_summary(
        self,
        previous_context: str,
        lookback_days: int
    ) -> str:
        """Get summarized context from LLM."""
        if not previous_context or previous_context == "Không có context từ các lần chạy trước.":
            return "Đây là lần phân tích đầu tiên, chưa có context từ các lần trước."
        
        prompt = self.prompt_loader.format(
            "context_summary",
            previous_context=previous_context,
            lookback_days=lookback_days
        )
        return await self._call_llm(prompt, max_tokens=1000)
    
    async def _call_llm(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.3
    ) -> str:
        """Make a call to Claude API."""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error calling LLM: {e}")
            raise
    
    def run_analysis_sync(
        self,
        news_articles: list[dict],
        indicators: list[dict],
        lookback_days: int = 7
    ) -> ParsedAnalysis:
        """Synchronous version of run_analysis for non-async contexts."""
        import asyncio
        return asyncio.run(self.run_analysis(news_articles, indicators, lookback_days))
