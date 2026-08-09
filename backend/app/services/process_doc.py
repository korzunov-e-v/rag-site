from sqlalchemy.orm import Session

from backend.app.db.enums import DocumentStatus
from backend.app.db.models import Document, DocumentChunk
from backend.app.services.chunking import split_text
from backend.app.services.embeddings import create_embeddings
from backend.app.services.extraction import get_text


def process_doc(document: Document, db: Session) -> None:
    document.status = DocumentStatus.PROCESSING
    db.commit()

    try:
        text = get_text(document.storage_path)

        if text is None:
            raise ValueError("Failed to extract document text")

        chunks = split_text(text)
        embeddings = create_embeddings(chunks)

        for chunk_index, (chunk, embedding) in enumerate(
            zip(chunks, embeddings)
        ):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk_index,
                    text=chunk,
                    embedding=embedding,
                )
            )

        document.status = DocumentStatus.PROCESSED
        db.commit()

    except Exception:
        document.status = DocumentStatus.FAILED
        db.commit()
        raise
