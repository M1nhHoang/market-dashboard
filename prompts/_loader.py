"""
Prompt Loader - Load and format prompts from markdown files.

This module provides a clean way to manage LLM prompts:
1. Prompts are stored as .md files for easy editing
2. Support for variable substitution using {variable_name} syntax
3. Caching to avoid repeated file reads
4. Clear separation between prompt content and code logic
"""

from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

from loguru import logger


class PromptLoader:
    """
    Load and format prompts from markdown files.
    
    Prompts are stored in the same directory as this module.
    Each prompt is a .md file with placeholders like {variable_name}.
    
    Example:
        loader = PromptLoader()
        
        # Get raw prompt
        template = loader.get("classification")
        
        # Get formatted prompt with variables
        prompt = loader.format("classification", 
            title="News Title",
            content="News Content"
        )
    """
    
    # Singleton instance
    _instance: Optional["PromptLoader"] = None
    
    def __new__(cls) -> "PromptLoader":
        """Singleton pattern - only one loader instance needed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the prompt loader."""
        if self._initialized:
            return
            
        self._prompts_dir = Path(__file__).parent
        self._cache: Dict[str, str] = {}
        self._initialized = True
        
        logger.debug(f"PromptLoader initialized with prompts dir: {self._prompts_dir}")
    
    @property
    def prompts_dir(self) -> Path:
        """Get the directory containing prompt files."""
        return self._prompts_dir
    
    def get(self, prompt_name: str) -> str:
        """
        Get a prompt template by name.
        
        Args:
            prompt_name: Name of the prompt (without .md extension)
            
        Returns:
            Raw prompt template string
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        # Check cache first
        if prompt_name in self._cache:
            return self._cache[prompt_name]
        
        # Build file path
        prompt_path = self._prompts_dir / f"{prompt_name}.md"
        
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}\n"
                f"Available prompts: {self.list_prompts()}"
            )
        
        # Read and cache
        content = prompt_path.read_text(encoding="utf-8")
        self._cache[prompt_name] = content
        
        logger.debug(f"Loaded prompt: {prompt_name} ({len(content)} chars)")
        return content
    
    def format(self, prompt_name: str, **kwargs: Any) -> str:
        """
        Get a prompt and format it with variables.
        
        Args:
            prompt_name: Name of the prompt (without .md extension)
            **kwargs: Variables to substitute in the prompt
            
        Returns:
            Formatted prompt string
            
        Example:
            prompt = loader.format("classification",
                title="SBV raises interest rates",
                content="The State Bank of Vietnam...",
                date="2026-02-05"
            )
        """
        template = self.get(prompt_name)
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # Log which variable was missing
            logger.error(f"Missing variable in prompt '{prompt_name}': {e}")
            logger.debug(f"Provided variables: {list(kwargs.keys())}")
            raise ValueError(
                f"Missing required variable {e} for prompt '{prompt_name}'"
            ) from e
    
    def format_safe(self, prompt_name: str, **kwargs: Any) -> str:
        """
        Get a prompt and format it, using empty string for missing variables.
        
        This is safer for optional variables but may hide errors.
        
        Args:
            prompt_name: Name of the prompt
            **kwargs: Variables to substitute
            
        Returns:
            Formatted prompt string (missing vars become empty)
        """
        template = self.get(prompt_name)
        
        # Use safe substitution that doesn't raise on missing keys
        import string
        
        class SafeDict(dict):
            def __missing__(self, key):
                return f"{{{key}}}"  # Keep placeholder if missing
        
        # Try format_map with SafeDict
        try:
            return template.format_map(SafeDict(**kwargs))
        except Exception as e:
            logger.warning(f"Error formatting prompt '{prompt_name}': {e}")
            return template
    
    def list_prompts(self) -> list[str]:
        """
        List all available prompt names.
        
        Returns:
            List of prompt names (without .md extension)
        """
        return [
            f.stem for f in self._prompts_dir.glob("*.md")
            if f.stem != "README"  # Exclude README if present
        ]
    
    def reload(self, prompt_name: str = None) -> None:
        """
        Clear cache to reload prompts from disk.
        
        Args:
            prompt_name: Specific prompt to reload, or None for all
        """
        if prompt_name:
            self._cache.pop(prompt_name, None)
            logger.debug(f"Cleared cache for prompt: {prompt_name}")
        else:
            self._cache.clear()
            logger.debug("Cleared all prompt cache")
    
    def get_variables(self, prompt_name: str) -> list[str]:
        """
        Extract variable names from a prompt template.
        
        Args:
            prompt_name: Name of the prompt
            
        Returns:
            List of variable names found in the template
        """
        import re
        
        template = self.get(prompt_name)
        
        # Find all {variable_name} patterns
        # Exclude {{ and }} which are escaped braces
        pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        matches = re.findall(pattern, template)
        
        # Return unique variable names
        return list(dict.fromkeys(matches))
    
    def validate(self, prompt_name: str, **kwargs: Any) -> tuple[bool, list[str]]:
        """
        Validate that all required variables are provided.
        
        Args:
            prompt_name: Name of the prompt
            **kwargs: Variables that would be provided
            
        Returns:
            Tuple of (is_valid, missing_variables)
        """
        required = set(self.get_variables(prompt_name))
        provided = set(kwargs.keys())
        missing = required - provided
        
        return len(missing) == 0, list(missing)


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

# Module-level loader instance
_loader: Optional[PromptLoader] = None


def _get_loader() -> PromptLoader:
    """Get or create the module-level loader instance."""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader


def get_prompt(prompt_name: str, **kwargs: Any) -> str:
    """
    Convenience function to get and format a prompt.
    
    Args:
        prompt_name: Name of the prompt (without .md extension)
        **kwargs: Variables to substitute
        
    Returns:
        Formatted prompt string
        
    Example:
        from prompts import get_prompt
        
        prompt = get_prompt("classification",
            title="SBV raises rates",
            content="...",
            source="SBV",
            date="2026-02-05"
        )
    """
    loader = _get_loader()
    
    if kwargs:
        return loader.format(prompt_name, **kwargs)
    else:
        return loader.get(prompt_name)


def list_prompts() -> list[str]:
    """
    Convenience function to list available prompts.
    
    Returns:
        List of prompt names
    """
    return _get_loader().list_prompts()


def reload_prompts() -> None:
    """Convenience function to clear prompt cache."""
    _get_loader().reload()
