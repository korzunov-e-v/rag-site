from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from backend.app.db.enums import DocumentStatus
from backend.app.db.connect import SessionLocal
from backend.app.db.models import Document, DocumentChunk
from backend.app.exceptions import RetryableError
from backend.app.tasks.documents import run_process_document
from backend.tests.conftest import auth_headers

TEXT = (
    "Компания производит ветрогенераторы. "
    "Гарантия на все модели составляет семь лет."
)


async def upload(client, headers, filename="doc.txt", content=TEXT.encode()):
    return await client.post(
        "/documents",
        headers=headers,
        files={"document": (filename, content, "text/plain")},
    )


class FakeTask:
    max_retries = 3

    def __init__(self, retries: int = 0):
        self.request = SimpleNamespace(retries=retries)

    def retry(self, exc, countdown):
        return RetryRequested(exc)


class RetryRequested(Exception):
    pass


async def test_upload_stores_file_and_queues_processing(client, storage, queued):
    headers = await auth_headers(client)

    response = await upload(client, headers)

    assert response.status_code == 200
    document = response.json()
    assert document["status"] == "uploaded"
    assert queued == [document["id"]]
    assert storage.files[f"documents/{document['id']}/doc.txt"] == TEXT.encode()


@pytest.mark.parametrize(
    ("filename", "content", "status_code"),
    [
        ("doc.exe", b"data", 415),
        ("doc.txt", b"", 400),
    ],
)
async def test_upload_validation(client, filename, content, status_code):
    headers = await auth_headers(client)

    response = await upload(client, headers, filename, content)

    assert response.status_code == status_code


async def test_documents_are_isolated_between_users(client):
    alice = await auth_headers(client, "alice@example.com")
    bob = await auth_headers(client, "bob@example.com")
    document_id = (await upload(client, alice)).json()["id"]

    bob_list = await client.get("/documents", headers=bob)
    bob_get = await client.get(f"/documents/{document_id}", headers=bob)
    bob_delete = await client.delete(f"/documents/{document_id}", headers=bob)
    alice_list = await client.get("/documents", headers=alice)

    assert bob_list.json() == []
    assert bob_get.status_code == 404
    assert bob_delete.status_code == 404
    assert [document["id"] for document in alice_list.json()] == [document_id]


async def test_delete_removes_document_file_and_chunks(client, storage, db):
    headers = await auth_headers(client)
    document_id = (await upload(client, headers)).json()["id"]
    await run_process_document(FakeTask(), document_id)

    response = await client.delete(f"/documents/{document_id}", headers=headers)

    assert response.status_code == 204
    assert storage.files == {}
    assert await db.scalar(select(func.count()).select_from(DocumentChunk)) == 0


async def test_processing_creates_chunks_and_reports_status(client, db, emitted):
    headers = await auth_headers(client)
    document_id = (await upload(client, headers)).json()["id"]

    await run_process_document(FakeTask(), document_id)

    document = await db.get(Document, document_id)
    chunks = (await db.scalars(select(DocumentChunk))).all()
    assert document.status == DocumentStatus.PROCESSED
    assert [chunk.text for chunk in chunks] == [TEXT]
    assert [status for _, status, _ in emitted] == ["processing", "processed"]


async def test_processing_unreadable_file_fails(client, db, emitted):
    headers = await auth_headers(client)
    document_id = (await upload(client, headers, content=bytes(range(256)) * 4)).json()["id"]

    with pytest.raises(ValueError):
        await run_process_document(FakeTask(), document_id)

    document = await db.get(Document, document_id)
    assert document.status == DocumentStatus.FAILED
    assert document.error_message == "Failed to extract document text"
    assert [status for _, status, _ in emitted] == ["processing", "failed"]


async def test_processing_retryable_error_keeps_processing_until_last_retry(
    client, db, emitted, monkeypatch
):
    headers = await auth_headers(client)
    document_id = (await upload(client, headers)).json()["id"]

    async def unavailable(values):
        raise RetryableError("Embedding provider temporarily unavailable")

    monkeypatch.setattr("backend.app.services.process_doc.create_embeddings", unavailable)

    with pytest.raises(RetryRequested):
        await run_process_document(FakeTask(retries=0), document_id)

    await db.refresh(await db.get(Document, document_id))
    assert (await db.get(Document, document_id)).status == DocumentStatus.PROCESSING
    assert "failed" not in [status for _, status, _ in emitted]

    with pytest.raises(RetryableError):
        await run_process_document(FakeTask(retries=3), document_id)

    document = await db.get(Document, document_id)
    await db.refresh(document)
    assert document.status == DocumentStatus.FAILED
    assert emitted[-1][1] == "failed"


async def test_processing_document_deleted_midway_finishes_quietly(client, emitted, monkeypatch):
    headers = await auth_headers(client)
    document_id = (await upload(client, headers)).json()["id"]

    async def delete_then_embed(values):
        async with SessionLocal() as other:
            await other.delete(await other.get(Document, document_id))
            await other.commit()
        return [[0.1] * 1536 for _ in values]

    monkeypatch.setattr("backend.app.services.process_doc.create_embeddings", delete_then_embed)

    await run_process_document(FakeTask(), document_id)

    assert [status for _, status, _ in emitted] == ["processing"]
