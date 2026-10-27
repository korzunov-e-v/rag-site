from types import SimpleNamespace

from backend.app.db.models import Document
from backend.app.tasks.documents import run_summarize
from backend.tests.conftest import auth_headers
from backend.tests.test_documents import FakeTask, upload
from backend.app.tasks.documents import run_process_document


def llm_reply(content):
    async def create(**kwargs):
        create.messages = kwargs["messages"]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    return create


async def test_processed_document_is_queued_for_summary(client, summarize_queued):
    headers = await auth_headers(client)
    document_id = (await upload(client, headers)).json()["id"]

    await run_process_document(FakeTask(), document_id)

    assert summarize_queued == [document_id]


async def test_summary_is_saved_and_sent_to_owner(client, db, monkeypatch):
    headers = await auth_headers(client)
    document_id = (await upload(client, headers)).json()["id"]
    await run_process_document(FakeTask(), document_id)

    events = []
    create = llm_reply("  Про ветрогенераторы и гарантию на них.  ")
    monkeypatch.setattr("backend.app.services.summary.client.chat.completions.create", create)
    monkeypatch.setattr(
        "backend.app.tasks.documents.emit_document_description",
        lambda *args: events.append(args),
    )

    await run_summarize(document_id)

    document = await db.get(Document, document_id)
    assert document.description == "Про ветрогенераторы и гарантию на них."
    assert events == [(document_id, document.description, document.owner_id)]
    assert "Гарантия на все модели" in create.messages[1]["content"]


async def test_summary_failure_does_not_touch_document(client, db, monkeypatch):
    headers = await auth_headers(client)
    document_id = (await upload(client, headers)).json()["id"]
    await run_process_document(FakeTask(), document_id)

    async def broken(**kwargs):
        raise RuntimeError("LLM is down")

    monkeypatch.setattr("backend.app.services.summary.client.chat.completions.create", broken)

    await run_summarize(document_id)

    document = await db.get(Document, document_id)
    assert document.description is None
    assert document.status.value == "processed"


def test_shorten_keeps_first_paragraph_and_cuts_on_boundaries():
    from backend.app.services.summary import shorten

    assert shorten("Про ветер.\n\nВопросы:\n* один") == "Про ветер."
    assert shorten("   ") is None

    long_sentences = "Первое предложение. " * 40
    assert shorten(long_sentences).endswith("предложение.")
    assert len(shorten(long_sentences)) <= 500

    one_long_sentence = "слово " * 200
    assert shorten(one_long_sentence).endswith("слово…")
