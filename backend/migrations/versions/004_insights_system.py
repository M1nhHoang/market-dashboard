"""Replace investigations with insights (signals, themes, watchlist)

Revision ID: 004_insights_system
Revises: 003_add_llm_call_history
Create Date: 2026-02-08 00:00:00.000000

This migration replaces the investigation system with the new insights system:
- Drops: investigations, investigation_evidence, predictions
- Creates: signals, themes, watchlist, signal_accuracy_stats

The new system provides:
- Signals: Auto-verifiable short-term predictions
- Themes: Aggregated topics with strength tracking
- Watchlist: User/system alerts and triggers
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_insights_system'
down_revision: Union[str, None] = '003_add_llm_call_history'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================================================
    # DROP OLD INVESTIGATION TABLES
    # ==================================================
    
    # Drop in reverse dependency order
    op.drop_table('investigation_evidence')
    op.drop_table('predictions')
    op.drop_table('investigations')
    
    # ==================================================
    # CREATE THEMES TABLE (first, as signals references it)
    # ==================================================
    
    op.create_table(
        'themes',
        sa.Column('id', sa.String(50), primary_key=True),
        # Core info
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('name_vi', sa.String(200), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        # Aggregation
        sa.Column('related_event_ids', sa.JSON, nullable=True),
        sa.Column('related_signal_ids', sa.JSON, nullable=True),
        sa.Column('related_indicators', sa.JSON, nullable=True),
        sa.Column('event_count', sa.Integer, default=1),
        # Strength
        sa.Column('strength', sa.Float, default=1.0),
        sa.Column('peak_strength', sa.Float, nullable=True),
        # Timing
        sa.Column('first_seen', sa.DateTime, nullable=True),
        sa.Column('last_seen', sa.DateTime, nullable=True),
        # Status
        sa.Column('status', sa.String(20), default='emerging'),
        # Template link
        sa.Column('template_id', sa.String(50), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('themes') as batch_op:
        batch_op.create_index('idx_themes_status', ['status'])
        batch_op.create_index('idx_themes_strength', ['strength'])
        batch_op.create_index('idx_themes_status_strength', ['status', 'strength'])
    
    # ==================================================
    # CREATE SIGNALS TABLE
    # ==================================================
    
    op.create_table(
        'signals',
        sa.Column('id', sa.String(50), primary_key=True),
        # Core prediction
        sa.Column('prediction', sa.Text, nullable=False),
        sa.Column('direction', sa.String(20), nullable=True),  # 'up', 'down', 'stable'
        sa.Column('target_indicator', sa.String(50), nullable=True),
        sa.Column('target_range_low', sa.Float, nullable=True),
        sa.Column('target_range_high', sa.Float, nullable=True),
        # Confidence & timing
        sa.Column('confidence', sa.String(20), default='medium'),
        sa.Column('timeframe_days', sa.Integer, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        # Source
        sa.Column('source_event_ids', sa.JSON, nullable=True),
        sa.Column('source_event_id', sa.String(50), nullable=True),
        sa.Column('reasoning', sa.Text, nullable=True),
        # Verification
        sa.Column('status', sa.String(30), default='active'),
        sa.Column('actual_value', sa.Float, nullable=True),
        sa.Column('verified_at', sa.DateTime, nullable=True),
        sa.Column('accuracy_notes', sa.Text, nullable=True),
        # Theme link
        sa.Column('theme_id', sa.String(50), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('signals') as batch_op:
        batch_op.create_index('idx_signals_status', ['status'])
        batch_op.create_index('idx_signals_expires_at', ['expires_at'])
        batch_op.create_index('idx_signals_target_indicator', ['target_indicator'])
        batch_op.create_index('idx_signals_status_expires', ['status', 'expires_at'])
        batch_op.create_index('idx_signals_confidence', ['confidence'])
        batch_op.create_index('idx_signals_theme_id', ['theme_id'])
        batch_op.create_foreign_key(
            'fk_signals_source_event', 
            'events', 
            ['source_event_id'], 
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_foreign_key(
            'fk_signals_theme', 
            'themes', 
            ['theme_id'], 
            ['id'],
            ondelete='SET NULL'
        )
    
    # ==================================================
    # CREATE WATCHLIST TABLE
    # ==================================================
    
    op.create_table(
        'watchlist',
        sa.Column('id', sa.String(50), primary_key=True),
        # Core info
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        # Trigger conditions
        sa.Column('trigger_type', sa.String(20), nullable=False),  # 'date', 'indicator', 'keyword'
        sa.Column('trigger_indicator', sa.String(50), nullable=True),
        sa.Column('trigger_condition', sa.String(100), nullable=True),
        sa.Column('trigger_keywords', sa.JSON, nullable=True),
        sa.Column('trigger_date', sa.Date, nullable=True),
        # Source
        sa.Column('source', sa.String(20), default='user'),
        sa.Column('template_id', sa.String(50), nullable=True),
        # Related
        sa.Column('related_indicators', sa.JSON, nullable=True),
        sa.Column('related_theme_id', sa.String(50), nullable=True),
        # Status
        sa.Column('status', sa.String(20), default='watching'),
        sa.Column('triggered_at', sa.DateTime, nullable=True),
        sa.Column('triggered_by_event_id', sa.String(50), nullable=True),
        sa.Column('trigger_value', sa.Float, nullable=True),
        # Snooze
        sa.Column('snoozed_until', sa.DateTime, nullable=True),
        # Created by
        sa.Column('created_by', sa.String(50), default='system'),
        # Timestamps
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('watchlist') as batch_op:
        batch_op.create_index('idx_watchlist_status', ['status'])
        batch_op.create_index('idx_watchlist_trigger_type', ['trigger_type'])
        batch_op.create_index('idx_watchlist_status_type', ['status', 'trigger_type'])
        batch_op.create_index('idx_watchlist_trigger_date', ['trigger_date'])
        batch_op.create_foreign_key(
            'fk_watchlist_theme', 
            'themes', 
            ['related_theme_id'], 
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_foreign_key(
            'fk_watchlist_triggered_event', 
            'events', 
            ['triggered_by_event_id'], 
            ['id'],
            ondelete='SET NULL'
        )
    
    # ==================================================
    # CREATE SIGNAL ACCURACY STATS TABLE
    # ==================================================
    
    op.create_table(
        'signal_accuracy_stats',
        sa.Column('id', sa.String(50), primary_key=True),
        # Grouping
        sa.Column('period', sa.String(20), nullable=False),  # 'daily', 'weekly', 'monthly', 'all_time'
        sa.Column('period_start', sa.Date, nullable=True),
        sa.Column('period_end', sa.Date, nullable=True),
        # Filter (optional)
        sa.Column('confidence_level', sa.String(20), nullable=True),
        sa.Column('indicator_id', sa.String(50), nullable=True),
        # Stats
        sa.Column('total_signals', sa.Integer, default=0),
        sa.Column('verified_correct', sa.Integer, default=0),
        sa.Column('verified_wrong', sa.Integer, default=0),
        sa.Column('expired', sa.Integer, default=0),
        sa.Column('accuracy_rate', sa.Float, nullable=True),
        # Timestamp
        sa.Column('calculated_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('signal_accuracy_stats') as batch_op:
        batch_op.create_index('idx_accuracy_period', ['period', 'period_start'])
    
    # ==================================================
    # UPDATE RUN_HISTORY TABLE (rename investigation columns to signal columns)
    # ==================================================
    
    with op.batch_alter_table('run_history') as batch_op:
        batch_op.alter_column('investigations_opened', new_column_name='signals_created')
        batch_op.alter_column('investigations_updated', new_column_name='themes_updated')
        batch_op.alter_column('investigations_resolved', new_column_name='watchlist_triggered')


def downgrade() -> None:
    # ==================================================
    # REVERT RUN_HISTORY COLUMN NAMES
    # ==================================================
    
    with op.batch_alter_table('run_history') as batch_op:
        batch_op.alter_column('signals_created', new_column_name='investigations_opened')
        batch_op.alter_column('themes_updated', new_column_name='investigations_updated')
        batch_op.alter_column('watchlist_triggered', new_column_name='investigations_resolved')
    
    # ==================================================
    # DROP NEW INSIGHT TABLES
    # ==================================================
    
    op.drop_table('signal_accuracy_stats')
    op.drop_table('watchlist')
    op.drop_table('signals')
    op.drop_table('themes')
    
    # ==================================================
    # RECREATE OLD INVESTIGATION TABLES
    # ==================================================
    
    op.create_table(
        'investigations',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('question', sa.Text, nullable=False),
        sa.Column('context', sa.Text, nullable=True),
        sa.Column('source_event_id', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), default='open'),
        sa.Column('priority', sa.String(20), default='medium'),
        sa.Column('evidence_count', sa.Integer, default=0),
        sa.Column('evidence_summary', sa.Text, nullable=True),
        sa.Column('resolution', sa.Text, nullable=True),
        sa.Column('resolution_confidence', sa.String(20), nullable=True),
        sa.Column('resolved_by_event_id', sa.String(50), nullable=True),
        sa.Column('last_evidence_at', sa.DateTime, nullable=True),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.Column('related_indicators', sa.JSON, nullable=True),
        sa.Column('related_templates', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    
    with op.batch_alter_table('investigations') as batch_op:
        batch_op.create_index('idx_investigations_status', ['status'])
    
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
        batch_op.create_foreign_key(
            'fk_evidence_investigation',
            'investigations',
            ['investigation_id'],
            ['id'],
            ondelete='CASCADE'
        )
        batch_op.create_foreign_key(
            'fk_evidence_event',
            'events',
            ['event_id'],
            ['id'],
            ondelete='SET NULL'
        )
    
    op.create_table(
        'predictions',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('prediction', sa.Text, nullable=False),
        sa.Column('based_on_events', sa.JSON, nullable=True),
        sa.Column('source_event_id', sa.String(50), nullable=True),
        sa.Column('investigation_id', sa.String(50), nullable=True),
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
        batch_op.create_index('idx_predictions_investigation', ['investigation_id'])
        batch_op.create_foreign_key(
            'fk_predictions_event',
            'events',
            ['source_event_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_foreign_key(
            'fk_predictions_investigation',
            'investigations',
            ['investigation_id'],
            ['id'],
            ondelete='SET NULL'
        )
