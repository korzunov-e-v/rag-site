import json
from types import SimpleNamespace

from backend.tests.conftest import auth_headers
from backend.tests.test_documents import FakeTask, upload
from backend.app.tasks.documents import run_process_document

WIND = "Гарантия на ветрогенераторы составляет семь лет."
SOUP = "Борщ варят из свёклы, капусты и картофеля."


async def add_document(client, headers, filename, text):
    document_id = (await upload(client, headers, filename, text.encode())).json()["id"]
    await run_process_document(FakeTask(), document_id)
    return document_id


async def test_search_returns_closest_chunk_of_own_documents(client):
    alice = await auth_headers(client, "alice@example.com")
    bob = await auth_headers(client, "bob@example.com")
    await add_document(client, alice, "wind.txt", WIND)
    await add_document(client, alice, "soup.txt", SOUP)
    await add_document(client, bob, "bob.txt", "Гарантия на ветрогенераторы Боба")

    response = await client.post(
        "/search",
        headers=alice,
        params={"query": "гарантия на ветрогенераторы"},
    )

    results = response.json()
    assert response.status_code == 200
    assert [result["text"] for result in results] == [WIND]


async def test_search_respects_max_distance(client, monkeypatch):
    headers = await auth_headers(client)
    await add_document(client, headers, "wind.txt", WIND)

    monkeypatch.setattr("backend.app.services.retrieval.settings.max_distance", 0.01)

    response = await client.post(
        "/search",
        headers=headers,
        params={"query": "гарантия на ветрогенераторы"},
    )

    assert response.json() == []


async def test_ask_answers_per_document_with_sources(client, monkeypatch):
    headers = await auth_headers(client)
    document_id = await add_document(client, headers, "wind.txt", WIND)

    async def create(**kwargs):
        content = json.dumps(
            {"answer": "Семь лет.", "quotes": ["семь лет"]},
            ensure_ascii=False,
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    monkeypatch.setattr("backend.app.services.ask.client.chat.completions.create", create)

    response = await client.post(
        "/ask",
        headers=headers,
        params={"query": "Какая гарантия на ветрогенераторы?"},
    )

    [answer] = response.json()
    assert answer["document_id"] == document_id
    assert answer["answer"] == "Семь лет."
    assert answer["sources"][0]["quote"] == "семь лет"
