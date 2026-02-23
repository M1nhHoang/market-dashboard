"""
LLM Client Base - Abstract base class for LLM providers.
"""
import uuid
import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextvars import ContextVar

from loguru import logger


# Context variables for passing metadata to logging
_current_task_type: ContextVar[Optional[str]] = ContextVar('task_type', default=None)
_current_run_id: ContextVar[Optional[str]] = ContextVar('run_id', default=None)


def set_llm_context(task_type: Optional[str] = None, run_id: Optional[str] = None):
    """Set context for LLM call logging."""
    if task_type is not None:
        _current_task_type.set(task_type)
    if run_id is not None:
        _current_run_id.set(run_id)


def get_llm_context() -> Dict[str, Optional[str]]:
    """Get current LLM logging context."""
    return {
        "task_type": _current_task_type.get(),
        "run_id": _current_run_id.get()
    }


@dataclass
class LLMResponse:
    """Standard response from LLM."""
    content: str
    model: str
    usage: Dict[str, int]  # input_tokens, output_tokens
    stop_reason: Optional[str] = None
    latency_ms: Optional[int] = None
    
    @property
    def total_tokens(self) -> int:
        return self.usage.get("input_tokens", 0) + self.usage.get("output_tokens", 0)


@dataclass
class Message:
    """Chat message."""
    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class LLMCallRecord:
    """Record of an LLM call for logging."""
    id: str
    timestamp: datetime
    model: str
    system_prompt: Optional[str]
    user_prompt: str
    messages: List[Dict[str, str]]
    response: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    temperature: float
    max_tokens: int
    latency_ms: Optional[int]
    stop_reason: Optional[str]
    task_type: Optional[str]
    run_id: Optional[str]
    is_valid_json: Optional[bool] = None


class LLMClient(ABC):
    """
    Abstract base class for LLM clients.
    
    All LLM providers should implement this interface.
    Includes automatic logging of all calls to database.
    """
    
    def __init__(self, api_key: str, model: str, enable_logging: bool = True):
        self.api_key = api_key
        self.model = model
        self.enable_logging = enable_logging
        self._pending_logs: List[LLMCallRecord] = []
    
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
    
    def _build_messages_for_log(
        self,
        messages: List[Message],
        system: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build messages list in OpenAI format for logging."""
        result = []
        if system:
            result.append({"role": "system", "content": system})
        for msg in messages:
            result.append({"role": msg.role, "content": msg.content})
        return result
    
    def _check_valid_json(self, content: str) -> bool:
        """Check if response is valid JSON."""
        import json
        try:
            json.loads(content)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    def _create_call_record(
        self,
        messages: List[Message],
        system: Optional[str],
        response: LLMResponse,
        max_tokens: int,
        temperature: float,
    ) -> LLMCallRecord:
        """Create a call record for logging."""
        context = get_llm_context()
        messages_for_log = self._build_messages_for_log(messages, system)
        
        # Extract user prompt (last user message)
        user_prompt = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_prompt = msg.content
                break
        
        return LLMCallRecord(
            id=f"llm_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow(),
            model=response.model,
            system_prompt=system,
            user_prompt=user_prompt,
            messages=messages_for_log,
            response=response.content,
            input_tokens=response.usage.get("input_tokens", 0),
            output_tokens=response.usage.get("output_tokens", 0),
            total_tokens=response.total_tokens,
            temperature=temperature,
            max_tokens=max_tokens,
            latency_ms=response.latency_ms,
            stop_reason=response.stop_reason,
            task_type=context.get("task_type"),
            run_id=context.get("run_id"),
            is_valid_json=self._check_valid_json(response.content),
        )
    
    def log_call(
        self,
        messages: List[Message],
        system: Optional[str],
        response: LLMResponse,
        max_tokens: int,
        temperature: float,
    ) -> None:
        """
        Log an LLM call directly to database.
        
        Saves the call record immediately using a background thread
        to avoid blocking the sync caller.
        """
        if not self.enable_logging:
            return
        
        record = self._create_call_record(
            messages=messages,
            system=system,
            response=response,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        logger.debug(f"LLM call logged: {record.id} ({record.task_type or 'unknown'})")
        
        # Save directly to database in a background thread
        self._save_record_to_db(record)
    
    def _save_record_to_db(self, record: LLMCallRecord) -> None:
        """
        Save a single LLM call record to database.
        
        Uses asyncio to run the async DB save. Handles the case where
        we may or may not be inside an existing event loop.
        """
        import threading
        
        async def _do_save():
            from database.session import get_session
            from database.models import LLMCallHistory
            
            try:
                async with get_session() as session:
                    db_record = LLMCallHistory(
                        id=record.id,
                        timestamp=record.timestamp,
                        model=record.model,
                        system_prompt=record.system_prompt,
                        user_prompt=record.user_prompt,
                        messages=record.messages,
                        response=record.response,
                        input_tokens=record.input_tokens,
                        output_tokens=record.output_tokens,
                        total_tokens=record.total_tokens,
                        temperature=record.temperature,
                        max_tokens=record.max_tokens,
                        latency_ms=record.latency_ms,
                        stop_reason=record.stop_reason,
                        task_type=record.task_type,
                        run_id=record.run_id,
                        is_valid_json=record.is_valid_json,
                    )
                    session.add(db_record)
                    await session.commit()
                    logger.debug(f"Saved LLM call log: {record.id}")
            except Exception as e:
                logger.error(f"Failed to save LLM call log {record.id}: {e}")
        
        # Run async save: use existing loop if available, otherwise create new one in thread
        try:
            loop = asyncio.get_running_loop()
            # We're inside an async context - schedule as a task
            loop.create_task(_do_save())
        except RuntimeError:
            # No running loop - run in a new thread with its own loop
            def _run():
                asyncio.run(_do_save())
            thread = threading.Thread(target=_run, daemon=True)
            thread.start()
    
    def get_pending_logs(self) -> List[LLMCallRecord]:
        """Get pending log records."""
        return self._pending_logs.copy()
    
    def clear_pending_logs(self) -> None:
        """Clear pending logs without saving."""
        self._pending_logs.clear()
    
    async def flush_logs_async(self) -> int:
        """
        Flush pending logs to database asynchronously.
        
        Returns:
            Number of records saved
        """
        if not self._pending_logs:
            return 0
        
        from database.session import get_session
        from database.models import LLMCallHistory
        
        records_to_save = self._pending_logs.copy()
        self._pending_logs.clear()
        
        try:
            async with get_session() as session:
                for record in records_to_save:
                    db_record = LLMCallHistory(
                        id=record.id,
                        timestamp=record.timestamp,
                        model=record.model,
                        system_prompt=record.system_prompt,
                        user_prompt=record.user_prompt,
                        messages=record.messages,
                        response=record.response,
                        input_tokens=record.input_tokens,
                        output_tokens=record.output_tokens,
                        total_tokens=record.total_tokens,
                        temperature=record.temperature,
                        max_tokens=record.max_tokens,
                        latency_ms=record.latency_ms,
                        stop_reason=record.stop_reason,
                        task_type=record.task_type,
                        run_id=record.run_id,
                        is_valid_json=record.is_valid_json,
                    )
                    session.add(db_record)
                await session.commit()
                logger.info(f"Flushed {len(records_to_save)} LLM call logs to database")
                return len(records_to_save)
        except Exception as e:
            logger.error(f"Failed to flush LLM logs: {e}")
            # Put back the records on failure
            self._pending_logs = records_to_save + self._pending_logs
            raise
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model})"
