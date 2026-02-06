"""
LLM Client Base - Abstract base class for LLM providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class LLMResponse:
    """Standard response from LLM."""
    content: str
    model: str
    usage: Dict[str, int]  # input_tokens, output_tokens
    stop_reason: Optional[str] = None
    
    @property
    def total_tokens(self) -> int:
        return self.usage.get("input_tokens", 0) + self.usage.get("output_tokens", 0)


@dataclass
class Message:
    """Chat message."""
    role: str  # "user", "assistant", "system"
    content: str


class LLMClient(ABC):
    """
    Abstract base class for LLM clients.
    
    All LLM providers should implement this interface.
    """
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """
        Generate a response from a single prompt.
        
        Args:
            prompt: The user prompt
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            
        Returns:
            LLMResponse with generated content
        """
        pass
    
    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """
        Generate a response from a conversation.
        
        Args:
            messages: List of conversation messages
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            LLMResponse with generated content
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model})"
