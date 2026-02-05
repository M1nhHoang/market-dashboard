"""
Context Summary Generator - Utility for summarizing previous context.
"""
import anthropic
from loguru import logger

from prompts import PromptLoader


def generate_context_summary(
    client: anthropic.Anthropic,
    model: str,
    previous_context: str,
    lookback_days: int = 7
) -> str:
    """
    Generate a summary of previous context for scoring prompt.
    
    This function uses LLM to condense previous analysis context
    into a digestible summary that can be included in scoring prompts.
    
    Args:
        client: Anthropic client instance
        model: LLM model name
        previous_context: Raw context string from previous runs
        lookback_days: Number of days the context covers
        
    Returns:
        Summarized context string
    """
    if not previous_context or previous_context.strip() == "":
        return "Đây là lần phân tích đầu tiên, chưa có context từ các lần trước."
    
    loader = PromptLoader()
    prompt = loader.format(
        "context_summary",
        previous_context=previous_context,
        lookback_days=lookback_days
    )
    
    try:
        response = client.messages.create(
            model=model,
            max_tokens=800,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Failed to generate context summary: {e}")
        return "Context summary generation failed."
