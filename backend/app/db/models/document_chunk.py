from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from backend.app.db.base import Base
from backend.app.db.models.document import Document
from backend.app.settings import settings


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    document: Mapped[Document] = relationship(
        back_populates="chunks",
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.openrouter_embedding_model_dimensions)
    )
