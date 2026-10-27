"""add hnsw index to chunk embeddings

Revision ID: 3f6c2a9d1b47
Revises: ed93b15dfdb3
Create Date: 2026-10-27 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3f6c2a9d1b47'
down_revision: Union[str, Sequence[str], None] = 'ed93b15dfdb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'ix_document_chunks_embedding_hnsw',
        'document_chunks',
        ['embedding'],
        postgresql_using='hnsw',
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )
    op.create_index(
        'ix_document_chunks_document_id',
        'document_chunks',
        ['document_id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_document_chunks_document_id', table_name='document_chunks')
    op.drop_index('ix_document_chunks_embedding_hnsw', table_name='document_chunks')
