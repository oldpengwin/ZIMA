"""drop the unused pgvector embedding column

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-08-12 18:40:00.000000

The `embedding` column and pgvector were declared but never populated or
queried — matching is pure archetype/skill math, not vector similarity.
Removing the column (and the pgvector dependency) rather than shipping a dead,
confusing extension. Re-add a current embedding library + column when semantic
search is actually built.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('profiles') as batch:
        batch.drop_column('embedding')

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
    # Re-add the embedding column as a plain float array (pgvector is intentionally gone).
    op.add_column('profiles', sa.Column('embedding', sa.ARRAY(sa.Float()), nullable=True))
