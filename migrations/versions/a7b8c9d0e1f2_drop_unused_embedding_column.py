"""organization ownership for real CRUD authz

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-08-12 18:40:00.000000

Originally this migration also dropped `profiles.embedding` (added by pgvector,
never populated or queried — matching is pure archetype/skill math, not vector
similarity). During the 13-Aug-2026 production audit the base migration
(ee6e2dd287ad) was edited to never create that column or import pgvector in the
first place, since a fresh install shouldn't need to install pgvector purely to
create-then-immediately-drop a column. That makes the drop here redundant (and
it would now fail outright — the column never existed), so it's removed; this
migration is now solely about organization ownership. Re-add a current
embedding library + column when semantic search is actually built.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organization ownership (for real CRUD authz — create/update/delete).
    op.add_column('organizations', sa.Column('owner_id', sa.UUID(), nullable=True))
    op.add_column('organizations', sa.Column('owner_deleted', sa.Boolean(), server_default='false', nullable=True))
    op.create_index(op.f('ix_organizations_owner_id'), 'organizations', ['owner_id'], unique=False)
    op.create_foreign_key(
        'fk_organizations_owner_id_profiles', 'organizations', 'profiles',
        ['owner_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_organizations_owner_id_profiles', 'organizations', type_='foreignkey')
    op.drop_index(op.f('ix_organizations_owner_id'), table_name='organizations')
    op.drop_column('organizations', 'owner_deleted')
    op.drop_column('organizations', 'owner_id')
