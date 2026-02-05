"""Add FK constraints, indexes, and new fields

Revision ID: 002_add_fk_constraints
Revises: 001_initial
Create Date: 2026-02-05 00:00:00.000000

This migration adds:
1. Foreign key constraints to all relationships
2. Hash index on events table
3. Unique constraint on calendar_events
4. New fields to run_history (raw_data_path, sources_crawled, crawl_stats)
5. investigation_id field to predictions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_fk_constraints'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================================================
    # EVENTS - Add hash index
    # ==================================================
    with op.batch_alter_table('events') as batch_op:
        batch_op.create_index('idx_events_hash', ['hash'])
    
    # ==================================================
    # INDICATOR_HISTORY - Add FK constraint
    # ==================================================
    with op.batch_alter_table('indicator_history') as batch_op:
        batch_op.create_foreign_key(
            'fk_indicator_history_indicator',
            'indicators',
            ['indicator_id'],
            ['id'],
            ondelete='CASCADE'
        )
    
    # ==================================================
    # CAUSAL_ANALYSES - Add FK constraint
    # ==================================================
    with op.batch_alter_table('causal_analyses') as batch_op:
        batch_op.create_foreign_key(
            'fk_causal_analyses_event',
            'events',
            ['event_id'],
            ['id'],
            ondelete='CASCADE'
        )
    
    # ==================================================
    # SCORE_HISTORY - Add FK constraint
    # ==================================================
    with op.batch_alter_table('score_history') as batch_op:
        batch_op.create_foreign_key(
            'fk_score_history_event',
            'events',
            ['event_id'],
            ['id'],
            ondelete='CASCADE'
        )
    
    # ==================================================
    # INVESTIGATION_EVIDENCE - Add FK constraints
    # ==================================================
    with op.batch_alter_table('investigation_evidence') as batch_op:
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
    
    # ==================================================
    # PREDICTIONS - Add investigation_id and FK constraints
    # ==================================================
    with op.batch_alter_table('predictions') as batch_op:
        # Add new column
        batch_op.add_column(
            sa.Column('investigation_id', sa.String(50), nullable=True)
        )
        # Add index
        batch_op.create_index('idx_predictions_investigation', ['investigation_id'])
        # Add FK constraints
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
    
    # ==================================================
    # RUN_HISTORY - Add new fields
    # ==================================================
    with op.batch_alter_table('run_history') as batch_op:
        batch_op.add_column(
            sa.Column('raw_data_path', sa.String(255), nullable=True)
        )
        batch_op.add_column(
            sa.Column('sources_crawled', sa.JSON, nullable=True)
        )
        batch_op.add_column(
            sa.Column('crawl_stats', sa.JSON, nullable=True)
        )
    
    # ==================================================
    # CALENDAR_EVENTS - Add unique constraint and index
    # ==================================================
    with op.batch_alter_table('calendar_events') as batch_op:
        batch_op.create_unique_constraint(
            'uq_calendar_event',
            ['date', 'event_name', 'country']
        )
        batch_op.create_index('idx_calendar_country', ['country'])


def downgrade() -> None:
    # ==================================================
    # CALENDAR_EVENTS - Remove constraint and index
    # ==================================================
    with op.batch_alter_table('calendar_events') as batch_op:
        batch_op.drop_index('idx_calendar_country')
        batch_op.drop_constraint('uq_calendar_event', type_='unique')
    
    # ==================================================
    # RUN_HISTORY - Remove new fields
    # ==================================================
    with op.batch_alter_table('run_history') as batch_op:
        batch_op.drop_column('crawl_stats')
        batch_op.drop_column('sources_crawled')
        batch_op.drop_column('raw_data_path')
    
    # ==================================================
    # PREDICTIONS - Remove FK and new column
    # ==================================================
    with op.batch_alter_table('predictions') as batch_op:
        batch_op.drop_constraint('fk_predictions_investigation', type_='foreignkey')
        batch_op.drop_constraint('fk_predictions_event', type_='foreignkey')
        batch_op.drop_index('idx_predictions_investigation')
        batch_op.drop_column('investigation_id')
    
    # ==================================================
    # INVESTIGATION_EVIDENCE - Remove FK constraints
    # ==================================================
    with op.batch_alter_table('investigation_evidence') as batch_op:
        batch_op.drop_constraint('fk_evidence_event', type_='foreignkey')
        batch_op.drop_constraint('fk_evidence_investigation', type_='foreignkey')
    
    # ==================================================
    # SCORE_HISTORY - Remove FK constraint
    # ==================================================
    with op.batch_alter_table('score_history') as batch_op:
        batch_op.drop_constraint('fk_score_history_event', type_='foreignkey')
    
    # ==================================================
    # CAUSAL_ANALYSES - Remove FK constraint
    # ==================================================
    with op.batch_alter_table('causal_analyses') as batch_op:
        batch_op.drop_constraint('fk_causal_analyses_event', type_='foreignkey')
    
    # ==================================================
    # INDICATOR_HISTORY - Remove FK constraint
    # ==================================================
    with op.batch_alter_table('indicator_history') as batch_op:
        batch_op.drop_constraint('fk_indicator_history_indicator', type_='foreignkey')
    
    # ==================================================
    # EVENTS - Remove hash index
    # ==================================================
    with op.batch_alter_table('events') as batch_op:
        batch_op.drop_index('idx_events_hash')
