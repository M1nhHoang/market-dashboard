"""Add LLM call history table

Revision ID: 003_add_llm_call_history
Revises: 002_add_fk_constraints
Create Date: 2026-02-07 00:00:00.000000

This migration adds:
1. llm_call_history table for storing all LLM API calls
2. Indexes for efficient querying by task_type, timestamp, run_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_llm_call_history'
down_revision: Union[str, None] = '002_add_fk_constraints'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================================================
    # LLM_CALL_HISTORY - Create table
    # ==================================================
    op.create_table(
        'llm_call_history',
        # Primary key
        sa.Column('id', sa.String(50), primary_key=True),
        
        # Timestamp
        sa.Column('timestamp', sa.DateTime, nullable=False, index=True),
        
        # Request details
        sa.Column('model', sa.String(50), nullable=False),
        sa.Column('system_prompt', sa.Text, nullable=True),
        sa.Column('user_prompt', sa.Text, nullable=False),
        
        # Full messages array (OpenAI format JSON)
        sa.Column('messages', sa.JSON, nullable=False),
        
        # Response
        sa.Column('response', sa.Text, nullable=False),
        
        # Token usage
        sa.Column('input_tokens', sa.Integer, nullable=False, default=0),
        sa.Column('output_tokens', sa.Integer, nullable=False, default=0),
        sa.Column('total_tokens', sa.Integer, nullable=False, default=0),
        
        # Request parameters
        sa.Column('temperature', sa.Float, nullable=False, default=0.0),
        sa.Column('max_tokens', sa.Integer, nullable=False, default=4096),
        
        # Performance
        sa.Column('latency_ms', sa.Integer, nullable=True),
        sa.Column('stop_reason', sa.String(50), nullable=True),
        
        # Metadata
        sa.Column('task_type', sa.String(50), nullable=True, index=True),
        sa.Column('run_id', sa.String(50), nullable=True, index=True),
        
        # Quality tracking
        sa.Column('is_valid_json', sa.Boolean, nullable=True),
        sa.Column('human_rating', sa.Integer, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
    )
    
    # Composite indexes
    op.create_index(
        'idx_llm_history_task_date',
        'llm_call_history',
        ['task_type', 'timestamp']
    )
    op.create_index(
        'idx_llm_history_run',
        'llm_call_history',
        ['run_id']
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_llm_history_run', table_name='llm_call_history')
    op.drop_index('idx_llm_history_task_date', table_name='llm_call_history')
    
    # Drop table
    op.drop_table('llm_call_history')
