"""Initial schema - All tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-01 00:00:00.000000

This is the initial migration that creates all database tables.
Based on the SQLAlchemy models defined in database/models/.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================================================
    # INDICATORS
    # ==================================================
    
    op.create_table(
        'indicators',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('name_vi', sa.String(200), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('subcategory', sa.String(50), nullable=True),
        sa.Column('value', sa.Float, nullable=True),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('change', sa.Float, nullable=True),
        sa.Column('change_pct', sa.Float, nullable=True),
        sa.Column('trend', sa.String(20), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('source_url', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    
    op.create_table(
        'indicator_history',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('indicator_id', sa.String(50), nullable=False),
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('previous_value', sa.Float, nullable=True),
        sa.Column('change', sa.Float, nullable=True),
        sa.Column('change_pct', sa.Float, nullable=True),
        sa.Column('volume', sa.Float, nullable=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('recorded_at', sa.DateTime, nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
    )
    
    with op.batch_alter_table('indicator_history') as batch_op:
        batch_op.create_index('idx_indicator_history_lookup', ['indicator_id', 'date'])
        batch_op.create_unique_constraint('uq_indicator_date_value', ['indicator_id', 'date', 'value'])
    
    # ==================================================
    # EVENTS
    # ==================================================
    
    op.create_table(
        'events',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('source_url', sa.Text, nullable=True),
        # Classification
        sa.Column('is_market_relevant', sa.Boolean, default=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('region', sa.String(50), nullable=True),
        sa.Column('linked_indicators', sa.JSON, nullable=True),
        # Scoring
        sa.Column('base_score', sa.Integer, nullable=True),
        sa.Column('score_factors', sa.JSON, nullable=True),
        # Ranking
        sa.Column('current_score', sa.Float, nullable=True),
        sa.Column('decay_factor', sa.Float, default=1.0),
        sa.Column('boost_factor', sa.Float, default=1.0),
        sa.Column('display_section', sa.String(50), nullable=True),
        sa.Column('hot_topic', sa.String(100), nullable=True),
        # Follow-up
        sa.Column('is_follow_up', sa.Boolean, default=False),
        sa.Column('follows_up_on', sa.String(50), nullable=True),
        # Metadata
        sa.Column('published_at', sa.DateTime, nullable=True),
        sa.Column('run_date', sa.Date, nullable=True),
        sa.Column('last_ranked_at', sa.DateTime, nullable=True),
        sa.Column('hash', sa.String(64), unique=True, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('events') as batch_op:
        batch_op.create_index('idx_events_display', ['display_section', 'current_score'])
        batch_op.create_index('idx_events_date', ['published_at'])
        batch_op.create_index('idx_events_run_date', ['run_date'])
        batch_op.create_index('idx_events_category', ['category'])
    
    op.create_table(
        'causal_analyses',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('event_id', sa.String(50), nullable=False),
        sa.Column('template_id', sa.String(50), nullable=True),
        sa.Column('chain_steps', sa.JSON, nullable=True),
        sa.Column('confidence', sa.String(20), nullable=True),
        sa.Column('needs_investigation', sa.JSON, nullable=True),
        sa.Column('affected_indicators', sa.JSON, nullable=True),
        sa.Column('impact_on_vn', sa.Text, nullable=True),
        sa.Column('reasoning', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('causal_analyses') as batch_op:
        batch_op.create_index('idx_causal_event', ['event_id'])
    
    op.create_table(
        'topic_frequency',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('topic', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('occurrence_count', sa.Integer, default=1),
        sa.Column('first_seen', sa.Date, nullable=True),
        sa.Column('last_seen', sa.Date, nullable=True),
        sa.Column('related_event_ids', sa.JSON, nullable=True),
        sa.Column('is_hot', sa.Boolean, default=False),
    )
    
    with op.batch_alter_table('topic_frequency') as batch_op:
        batch_op.create_index('idx_topic', ['topic'])
    
    op.create_table(
        'score_history',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('event_id', sa.String(50), nullable=False),
        sa.Column('score', sa.Float, nullable=True),
        sa.Column('decay_factor', sa.Float, nullable=True),
        sa.Column('boost_factor', sa.Float, nullable=True),
        sa.Column('display_section', sa.String(50), nullable=True),
        sa.Column('recorded_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('score_history') as batch_op:
        batch_op.create_index('idx_score_event', ['event_id'])
    
    # ==================================================
    # INVESTIGATIONS
    # ==================================================
    
    op.create_table(
        'investigations',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('question', sa.Text, nullable=False),
        sa.Column('context', sa.Text, nullable=True),
        sa.Column('source_event_id', sa.String(50), nullable=True),
        # Status
        sa.Column('status', sa.String(20), default='open'),
        sa.Column('priority', sa.String(20), default='medium'),
        # Evidence
        sa.Column('evidence_count', sa.Integer, default=0),
        sa.Column('evidence_summary', sa.Text, nullable=True),
        # Resolution
        sa.Column('resolution', sa.Text, nullable=True),
        sa.Column('resolution_confidence', sa.String(20), nullable=True),
        sa.Column('resolved_by_event_id', sa.String(50), nullable=True),
        # Timestamps
        sa.Column('last_evidence_at', sa.DateTime, nullable=True),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        # Related
        sa.Column('related_indicators', sa.JSON, nullable=True),
        sa.Column('related_templates', sa.JSON, nullable=True),
    )
    
    with op.batch_alter_table('investigations') as batch_op:
        batch_op.create_index('idx_investigation_status', ['status'])
    
    op.create_table(
        'investigation_evidence',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('investigation_id', sa.String(50), nullable=False),
        sa.Column('event_id', sa.String(50), nullable=True),
        sa.Column('evidence_type', sa.String(20), nullable=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('added_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('investigation_evidence') as batch_op:
        batch_op.create_index('idx_evidence_investigation', ['investigation_id'])
    
    op.create_table(
        'predictions',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('prediction', sa.Text, nullable=False),
        sa.Column('based_on_events', sa.JSON, nullable=True),
        sa.Column('source_event_id', sa.String(50), nullable=True),
        sa.Column('confidence', sa.String(20), nullable=True),
        sa.Column('check_by_date', sa.Date, nullable=True),
        sa.Column('verification_indicator', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('actual_outcome', sa.Text, nullable=True),
        sa.Column('verified_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('predictions') as batch_op:
        batch_op.create_index('idx_predictions_status', ['status'])
        batch_op.create_index('idx_predictions_check_date', ['check_by_date'])
    
    # ==================================================
    # SYSTEM
    # ==================================================
    
    op.create_table(
        'run_history',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('run_date', sa.Date, nullable=True),
        sa.Column('run_time', sa.DateTime, nullable=True),
        sa.Column('news_count', sa.Integer, nullable=True),
        sa.Column('events_extracted', sa.Integer, nullable=True),
        sa.Column('events_key', sa.Integer, nullable=True),
        sa.Column('events_other', sa.Integer, nullable=True),
        sa.Column('investigations_opened', sa.Integer, nullable=True),
        sa.Column('investigations_updated', sa.Integer, nullable=True),
        sa.Column('investigations_resolved', sa.Integer, nullable=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
    )
    
    with op.batch_alter_table('run_history') as batch_op:
        batch_op.create_index('idx_run_date', ['run_date'])
    
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('date', sa.Date, nullable=True),
        sa.Column('time', sa.Time, nullable=True),
        sa.Column('event_name', sa.Text, nullable=True),
        sa.Column('country', sa.String(10), nullable=True),
        sa.Column('importance', sa.String(20), nullable=True),
        sa.Column('forecast', sa.String(50), nullable=True),
        sa.Column('previous', sa.String(50), nullable=True),
        sa.Column('actual', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('calendar_events') as batch_op:
        batch_op.create_index('idx_calendar_date', ['date'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('calendar_events')
    op.drop_table('run_history')
    op.drop_table('predictions')
    op.drop_table('investigation_evidence')
    op.drop_table('investigations')
    op.drop_table('score_history')
    op.drop_table('topic_frequency')
    op.drop_table('causal_analyses')
    op.drop_table('events')
    op.drop_table('indicator_history')
    op.drop_table('indicators')
