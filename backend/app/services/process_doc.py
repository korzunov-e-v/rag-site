from sqlalchemy.orm import Session

from backend.app.db.models import Document, DocumentChunk
from backend.app.services.chunking import split_text
from backend.app.services.embeddings import create_embeddings
from backend.app.services.extraction import get_text


def process_doc(db_document: Document, db: Session):
    text = get_text(db_document.storage_path)
    if text is not None:
        print(len(text))
        print(db_document.filename)
        chunks = split_text(text)
        embeddings = create_embeddings(chunks)
        for chunk_index, chunk in enumerate(chunks):
            db_chunk = DocumentChunk(
                document_id=db_document.id,
                chunk_index=chunk_index,
                text=chunk,
                embedding=embeddings[chunk_index],
            )
            db.add(db_chunk)
        db.commit()

