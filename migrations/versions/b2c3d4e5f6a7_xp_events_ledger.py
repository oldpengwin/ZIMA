"""xp events ledger for Discord gamification

Adds the append-only `xp_events` table backing services/xp_service.py. Total XP
and level are derived by summing this table, so there is no mutable xp/level
column on `profiles` — the ledger is the single source of truth. The unique
(discord_id, event_type, ref_id) constraint is what makes awards idempotent:
once-per-user events use ref_id='' (can only land once); repeatable events pass
the triggering entity id as ref_id (each distinct entity awards once).

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-08-13 09:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'xp_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('discord_id', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('ref_id', sa.String(length=100), server_default='', nullable=False),
        sa.Column('points', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('discord_id', 'event_type', 'ref_id', name='_discord_xp_event_uc'),
    )
    op.create_index(op.f('ix_xp_events_discord_id'), 'xp_events', ['discord_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_xp_events_discord_id'), table_name='xp_events')
    op.drop_table('xp_events')
