"""neurotype typology quiz: two neurotypes + quiz_responses

Revision ID: f1a2b3c4d5e6
Revises: 8064a67142d0
Create Date: 2026-08-12 16:20:00.000000

Adds the assessed/identified neurotype columns (two-badge system) to profiles
and the append-only quiz_responses table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '8064a67142d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('profiles', sa.Column('assessed_neurotype', sa.String(length=20), nullable=True))
    op.add_column('profiles', sa.Column('identified_neurotype', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_profiles_assessed_neurotype'), 'profiles', ['assessed_neurotype'], unique=False)
    op.create_index(op.f('ix_profiles_identified_neurotype'), 'profiles', ['identified_neurotype'], unique=False)

    op.create_table(
        'quiz_responses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('profile_id', sa.UUID(), nullable=False),
        sa.Column('quiz_version', sa.String(length=20), nullable=False),
        sa.Column('answers', sa.JSON(), server_default='{}', nullable=False),
        sa.Column('scores', sa.JSON(), server_default='{}', nullable=False),
        sa.Column('assessed_neurotype', sa.String(length=20), nullable=True),
        sa.Column('identified_neurotype', sa.String(length=20), nullable=True),
        sa.Column('source', sa.String(length=20), server_default='web', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_quiz_responses_profile_id'), 'quiz_responses', ['profile_id'], unique=False)
    op.create_index(op.f('ix_quiz_responses_created_at'), 'quiz_responses', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_quiz_responses_created_at'), table_name='quiz_responses')
    op.drop_index(op.f('ix_quiz_responses_profile_id'), table_name='quiz_responses')
    op.drop_table('quiz_responses')
    op.drop_index(op.f('ix_profiles_identified_neurotype'), table_name='profiles')
    op.drop_index(op.f('ix_profiles_assessed_neurotype'), table_name='profiles')
    op.drop_column('profiles', 'identified_neurotype')
    op.drop_column('profiles', 'assessed_neurotype')
