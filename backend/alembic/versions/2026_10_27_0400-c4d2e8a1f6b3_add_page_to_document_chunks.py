"""add page to document chunks

Revision ID: c4d2e8a1f6b3
Revises: 8b1e4f7c2d90
Create Date: 2026-10-27 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d2e8a1f6b3'
down_revision: Union[str, Sequence[str], None] = '8b1e4f7c2d90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('document_chunks', sa.Column('page', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('document_chunks', 'page')
