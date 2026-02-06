"""
LLM Call History Model

Stores all LLM API calls for fine-tuning and analysis.
Format compatible with OpenAI fine-tuning format.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Integer, Float, DateTime, Text, Boolean, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LLMCallHistory(Base):
    """
    LLM Call History for fine-tuning dataset.
    
    Stores every LLM API call with full input/output.
    Can be exported to OpenAI fine-tune JSONL format:
    {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
    """
    __tablename__ = "llm_call_history"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        index=True
    )
    
    # Request details
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Full messages array (OpenAI format)
    # [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]
    messages: Mapped[List[Dict[str, str]]] = mapped_column(JSON, nullable=False)
    
    # Response
    response: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Token usage
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Request parameters
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)
    
    # Performance
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stop_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Metadata for context
    task_type: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True,
        index=True
    )  # 'classification', 'scoring', 'ranking', 'investigation_review', 'context_summary'
    
    run_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    # Quality tracking (for future RLHF)
    is_valid_json: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    human_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5 scale
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_llm_history_task_date', 'task_type', 'timestamp'),
        Index('idx_llm_history_run', 'run_id'),
    )
    
    def to_openai_format(self) -> Dict[str, Any]:
        """
        Export to OpenAI fine-tuning format.
        
        Returns:
            Dict in format: {"messages": [...]}
        """
        messages = list(self.messages)  # Copy the input messages
        
        # Add assistant response
        messages.append({
            "role": "assistant",
            "content": self.response
        })
        
        return {"messages": messages}
    
    def __repr__(self) -> str:
        return f"<LLMCallHistory(id={self.id}, task={self.task_type}, tokens={self.total_tokens})>"
