"""add is_shared to documents

Revision ID: 5a7b9c3d1e2f
Revises: c4d2e8a1f6b3
Create Date: 2026-10-27 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a7b9c3d1e2f'
down_revision: Union[str, Sequence[str], None] = 'c4d2e8a1f6b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'documents',
        sa.Column('is_shared', sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index(op.f('ix_documents_owner_id'), 'documents', ['owner_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_documents_owner_id'), table_name='documents')
    op.drop_column('documents', 'is_shared')
