import asyncio
import tempfile
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Document, DocumentChunk
from backend.app.services.chunking import split_sections
from backend.app.services.embeddings import create_embeddings
from backend.app.services.extraction import extract_sections
from backend.app.services.storage import s3_storage


async def process_doc(
    document: Document,
    db: AsyncSession,
) -> None:
    with tempfile.NamedTemporaryFile() as temp_file:
        file = await asyncio.to_thread(
            s3_storage.download,
            document.storage_key,
        )

        temp_file.write(file.read())
        temp_file.flush()

        sections = await asyncio.to_thread(
            extract_sections,
            Path(temp_file.name),
        )

    if not sections:
        raise ValueError(
            "Failed to extract document text"
        )

    chunks = split_sections(sections)

    if not chunks:
        raise ValueError(
            "Document contains no text"
        )

    embeddings = await create_embeddings([chunk.text for chunk in chunks])

    await db.execute(
        delete(DocumentChunk).where(
            DocumentChunk.document_id == document.id
        )
    )

    for chunk_index, (chunk, embedding) in enumerate(
        zip(chunks, embeddings)
    ):
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=chunk_index,
                text=chunk.text,
                page=chunk.page,
                embedding=embedding,
            )
        )
