from sqlalchemy.orm import Session

from backend.app.db.models import Document, DocumentChunk
from backend.app.services.chunking import split_text
from backend.app.services.embeddings import create_embeddings
from backend.app.services.extraction import get_text


def process_doc(document: Document, db: Session) -> None:
    text = get_text(document.storage_path)

    if text is None:
        return

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

    db.commit()
