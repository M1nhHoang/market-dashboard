"""
Prompts Module - Centralized prompt management for LLM Pipeline.

This module provides:
- PromptLoader: Class to load prompts from markdown files
- All prompt templates as markdown files

Usage:
    from prompts import PromptLoader, get_prompt
    
    # Using class
    loader = PromptLoader()
    prompt = loader.get("classification")
    formatted = loader.format("classification", title="...", content="...")
    
    # Using convenience function
    prompt = get_prompt("scoring", title="...", content="...")

Prompt Files:
- classification.md: Layer 1 - News classification
- scoring.md: Layer 2 - News scoring and analysis
- context_summary.md: Context summarization for Layer 2
- main_analysis.md: Main analysis prompt
"""

from ._loader import PromptLoader, get_prompt, list_prompts

__all__ = [
    "PromptLoader",
    "get_prompt",
    "list_prompts",
]
