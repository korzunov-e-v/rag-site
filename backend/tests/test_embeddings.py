from types import SimpleNamespace

from backend.app.services import embeddings


async def test_create_embeddings_sends_batches_and_keeps_order(monkeypatch):
    calls = []

    async def create(model, input):
        calls.append(list(input))
        # Провайдер может вернуть элементы не по порядку — ориентируемся на index.
        data = [
            SimpleNamespace(index=index, embedding=[float(text)])
            for index, text in enumerate(input)
        ]
        return SimpleNamespace(data=list(reversed(data)))

    monkeypatch.setattr(embeddings.settings, "embedding_batch_size", 2)
    monkeypatch.setattr(embeddings.client.embeddings, "create", create)

    result = await embeddings.create_embeddings(["1", "2", "3", "4", "5"])

    assert calls == [["1", "2"], ["3", "4"], ["5"]]
    assert result == [[1.0], [2.0], [3.0], [4.0], [5.0]]
