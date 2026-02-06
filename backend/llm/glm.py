"""
GLM Client - Z.AI GLM-4.7 implementation.

Uses OpenAI-compatible API from Z.AI.
API docs: https://docs.z.ai/guides/develop/openai/python
"""
from typing import Optional, List

import httpx
from openai import OpenAI
from loguru import logger

from .base import LLMClient, LLMResponse, Message


class GLMClient(LLMClient):
    """
    Z.AI GLM client using OpenAI-compatible API.
    
    Supports GLM-4.7, GLM-4.5-air and other Z.AI models.
    Uses OpenAI SDK for maximum compatibility.
    
    Note: Uses Coding Plan API endpoint by default.
    """
    
    # Coding Plan API (for dev tools) - use this if you have Coding Plan subscription
    API_BASE = "https://api.z.ai/api/coding/paas/v4"
    
    # General API (uncomment if you have general API subscription)
    # API_BASE = "https://api.z.ai/api/paas/v4/"
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "glm-4.7",
        timeout: float = 120.0,
        verify_ssl: bool = True
    ):
        """
        Initialize GLM client.
        
        Args:
            api_key: Z.AI API key
            model: Model name (glm-4.7, glm-4.5-air, etc.)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates (disable for dev if needed)
        """
        super().__init__(api_key, model)
        self.timeout = timeout
        
        # Create custom httpx client if SSL verification needs to be disabled
        http_client = None
        if not verify_ssl:
            http_client = httpx.Client(verify=False)
            logger.warning("SSL verification disabled for GLM client")
        
        self._client = OpenAI(
            api_key=api_key,
            base_url=self.API_BASE,
            timeout=timeout,
            http_client=http_client,
        )
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate response from a single prompt."""
        messages = [Message(role="user", content=prompt)]
        return self.chat(messages, system=system, max_tokens=max_tokens, temperature=temperature)
    
    def chat(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate response from conversation."""
        # Build messages list
        api_messages = []
        
        # Add system message if provided
        if system:
            api_messages.append({"role": "system", "content": system})
        
        # Add conversation messages
        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})
        
        logger.debug(f"GLM request: model={self.model}, messages={len(api_messages)}")
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            # Parse response
            choice = response.choices[0]
            usage = response.usage
            
            return LLMResponse(
                content=choice.message.content,
                model=response.model,
                usage={
                    "input_tokens": usage.prompt_tokens if usage else 0,
                    "output_tokens": usage.completion_tokens if usage else 0,
                },
                stop_reason=choice.finish_reason,
            )
            
        except Exception as e:
            logger.error(f"GLM request failed: {e}")
            raise
