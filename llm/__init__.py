"""
LLM Module - Unified interface for LLM providers.

Usage:
    from llm import get_client
    
    client = get_client()  # Uses config settings
    response = client.generate("Your prompt here")
    print(response.content)

Supported providers:
- glm: Z.AI GLM-4.7 via OpenAI-compatible API
"""
from typing import Optional

from config import settings
from .base import LLMClient, LLMResponse, Message
from .glm import GLMClient


# Provider mapping
_PROVIDERS = {
    "glm": GLMClient,
}

# Default models per provider
_DEFAULT_MODELS = {
    "glm": "glm-4.7",
}


def get_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    verify_ssl: Optional[bool] = None,
) -> LLMClient:
    """
    Get an LLM client instance.
    
    Args:
        provider: Provider name ("glm"). Defaults to settings.LLM_PROVIDER
        api_key: API key. Defaults to settings based on provider
        model: Model name. Defaults to settings.LLM_MODEL or provider default
        verify_ssl: Whether to verify SSL. Defaults to settings.LLM_VERIFY_SSL
        
    Returns:
        Configured LLMClient instance
        
    Example:
        client = get_client()
        response = client.generate("Summarize this: ...")
    """
    # Determine provider
    provider = provider or getattr(settings, "LLM_PROVIDER", "glm")
    provider = provider.lower()
    
    if provider not in _PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {provider}. Available: {list(_PROVIDERS.keys())}")
    
    # Get API key
    if api_key is None:
        if provider == "glm":
            api_key = settings.GLM_API_KEY
        else:
            raise ValueError(f"No API key configured for provider: {provider}")
    
    if not api_key:
        raise ValueError(f"API key required for provider: {provider}")
    
    # Get model
    model = model or settings.LLM_MODEL or _DEFAULT_MODELS.get(provider)
    
    # Get SSL verification setting
    if verify_ssl is None:
        verify_ssl = getattr(settings, "LLM_VERIFY_SSL", True)
    
    # Create client
    client_class = _PROVIDERS[provider]
    return client_class(api_key=api_key, model=model, verify_ssl=verify_ssl)


__all__ = [
    "get_client",
    "LLMClient",
    "LLMResponse",
    "Message",
    "GLMClient",
]
