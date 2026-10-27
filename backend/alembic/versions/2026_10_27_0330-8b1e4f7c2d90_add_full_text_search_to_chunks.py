"""add full text search to chunks

Revision ID: 8b1e4f7c2d90
Revises: 3f6c2a9d1b47
Create Date: 2026-10-27 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8b1e4f7c2d90'
down_revision: Union[str, Sequence[str], None] = '3f6c2a9d1b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'document_chunks',
        sa.Column(
            'search_vector',
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('russian', text)", persisted=True),
            nullable=True,
        ),
    )
    op.create_index(
        'ix_document_chunks_search_vector',
        'document_chunks',
        ['search_vector'],
        postgresql_using='gin',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_document_chunks_search_vector', table_name='document_chunks')
    op.drop_column('document_chunks', 'search_vector')
