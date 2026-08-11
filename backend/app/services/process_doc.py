import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.db.enums import DocumentStatus
from backend.app.db.models import Document, DocumentChunk
from backend.app.services.chunking import split_text
from backend.app.services.embeddings import create_embeddings
from backend.app.services.extraction import get_text
from backend.app.services.storage import s3_storage
from backend.app.socketio_publisher import emit_document_status

def process_doc(document: Document, db: Session) -> None:
    document.status = DocumentStatus.PROCESSING
    db.commit()
    emit_document_status(
        document.id,
        DocumentStatus.PROCESSING.value,
    )

    try:
        with tempfile.NamedTemporaryFile() as temp_file:
            file = s3_storage.download(document.storage_key)

            temp_file.write(file.read())
            temp_file.flush()

            text = get_text(Path(temp_file.name))

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

        emit_document_status(
            document.id,
            DocumentStatus.PROCESSED.value,
        )


    except Exception:
        document.status = DocumentStatus.FAILED
        db.commit()
        emit_document_status(
            document.id,
            DocumentStatus.FAILED.value,
        )
        raise
