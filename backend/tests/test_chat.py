import json
from types import SimpleNamespace

from sqlalchemy import select

from backend.app.db.models import Conversation, Message, User
from backend.app.services import agent
from backend.app.services.chat import NOTHING_FOUND, handle_ask
from backend.tests.conftest import auth_headers
from backend.tests.test_rag import WIND, add_document


def tool_call(name, **arguments):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[
            SimpleNamespace(function=SimpleNamespace(name=name, arguments=json.dumps(arguments, ensure_ascii=False)))
        ]))]
    )


def answer(text, quotes):
    content = json.dumps({"answer": text, "quotes": quotes}, ensure_ascii=False)
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeLLM:
    """Отвечает агенту заданными вызовами инструментов, а на вопросы по документам — answer()."""

    def __init__(self, *decisions):
        self.decisions = list(decisions)
        self.agent_calls = []

    async def create(self, **kwargs):
        if "tools" in kwargs:
            self.agent_calls.append(kwargs)
            return self.decisions.pop(0)
        return answer("Семь лет.", ["семь лет"])


class Events(list):
    async def __call__(self, event, payload):
        self.append((event, payload))

    def names(self):
        return [event for event, _ in self]


async def user_id(db, email="user@example.com"):
    return await db.scalar(select(User.id).where(User.email == email))


async def test_search_with_rewritten_query_saves_conversation(client, db, monkeypatch):
    headers = await auth_headers(client)
    await add_document(client, headers, "wind.txt", WIND)
    llm = FakeLLM(tool_call("search_documents", query="Какая гарантия на ветрогенераторы?"))
    monkeypatch.setattr("backend.app.llm.openrouter.client.chat.completions.create", llm.create)
    events = Events()

    await handle_ask(db, await user_id(db), "гарантия?", None, events)

    assert events.names() == ["ask:started", "ask:searching", "answer", "ask:finished"]
    assert events[1][1] == {"query": "Какая гарантия на ветрогенераторы?"}
    assert events[2][1]["answer"] == "Семь лет."

    conversation = await db.scalar(select(Conversation))
    messages = list(await db.scalars(select(Message).order_by(Message.id)))
    assert conversation.title == "гарантия?"
    assert [(m.role.value, m.kind.value) for m in messages] == [("user", "question"), ("assistant", "answers")]
    assert messages[1].answers[0]["filename"] == "wind.txt"
    assert "wind.txt" in llm.agent_calls[0]["messages"][0]["content"]


async def test_follow_up_question_sees_history(client, db, monkeypatch):
    headers = await auth_headers(client)
    await add_document(client, headers, "wind.txt", WIND)
    llm = FakeLLM(
        tool_call("search_documents", query="Какая гарантия на ветрогенераторы?"),
        tool_call("search_documents", query="Какая гарантия на лопасти?"),
    )
    monkeypatch.setattr("backend.app.llm.openrouter.client.chat.completions.create", llm.create)
    events = Events()
    owner = await user_id(db)

    await handle_ask(db, owner, "Какая гарантия?", None, events)
    conversation_id = events[0][1]["conversation_id"]
    await handle_ask(db, owner, "а на лопасти?", conversation_id, events)

    history = llm.agent_calls[1]["messages"]
    assert [message["role"] for message in history] == ["system", "user", "assistant", "user"]
    assert history[1]["content"] == "Какая гарантия?"
    assert history[2]["content"] == "wind.txt: Семь лет."
    assert history[3]["content"] == "а на лопасти?"
    assert await db.scalar(select(Conversation.id)) == conversation_id


async def test_clarification_and_reply_skip_search(client, db, monkeypatch):
    await auth_headers(client)
    llm = FakeLLM(
        tool_call("ask_clarification", question="О каком документе речь?"),
        tool_call("reply", text="Привет! Задайте вопрос по документам."),
    )
    monkeypatch.setattr("backend.app.llm.openrouter.client.chat.completions.create", llm.create)
    events = Events()
    owner = await user_id(db)

    await handle_ask(db, owner, "а сколько?", None, events)
    await handle_ask(db, owner, "привет", events[0][1]["conversation_id"], events)

    assert events.names() == [
        "ask:started", "clarification", "ask:finished",
        "ask:started", "reply", "ask:finished",
    ]
    kinds = [m.kind.value for m in await db.scalars(select(Message).order_by(Message.id))]
    assert kinds == ["question", "clarification", "question", "reply"]


async def test_agent_failure_falls_back_to_search_with_original_query(client, db, monkeypatch):
    await auth_headers(client)

    async def broken(**kwargs):
        raise RuntimeError("LLM is down")

    monkeypatch.setattr("backend.app.llm.openrouter.client.chat.completions.create", broken)

    decision = await agent.decide("Какая гарантия?", [], db, await user_id(db))

    assert (decision.action, decision.text) == ("search", "Какая гарантия?")


async def test_nothing_found_is_reported(client, db, monkeypatch):
    await auth_headers(client)
    llm = FakeLLM(tool_call("search_documents", query="Какая гарантия?"))
    monkeypatch.setattr("backend.app.llm.openrouter.client.chat.completions.create", llm.create)
    events = Events()

    await handle_ask(db, await user_id(db), "Какая гарантия?", None, events)

    assert ("reply", {"text": NOTHING_FOUND}) in events


async def test_foreign_conversation_id_starts_new_conversation(client, db, monkeypatch):
    await auth_headers(client, "alice@example.com")
    await auth_headers(client, "bob@example.com")
    llm = FakeLLM(tool_call("reply", text="Привет"), tool_call("reply", text="Привет"))
    monkeypatch.setattr("backend.app.llm.openrouter.client.chat.completions.create", llm.create)
    events = Events()

    await handle_ask(db, await user_id(db, "alice@example.com"), "привет", None, events)
    alice_conversation = events[0][1]["conversation_id"]
    await handle_ask(db, await user_id(db, "bob@example.com"), "привет", alice_conversation, events)

    assert events[3][1]["conversation_id"] != alice_conversation


async def test_conversations_api(client, db, monkeypatch):
    headers = await auth_headers(client, "alice@example.com")
    bob = await auth_headers(client, "bob@example.com")
    llm = FakeLLM(tool_call("reply", text="Привет!"))
    monkeypatch.setattr("backend.app.llm.openrouter.client.chat.completions.create", llm.create)
    events = Events()
    await handle_ask(db, await user_id(db, "alice@example.com"), "привет", None, events)
    conversation_id = events[0][1]["conversation_id"]

    listed = await client.get("/conversations", headers=headers)
    detail = await client.get(f"/conversations/{conversation_id}", headers=headers)
    foreign = await client.get(f"/conversations/{conversation_id}", headers=bob)
    deleted = await client.delete(f"/conversations/{conversation_id}", headers=headers)

    assert [c["title"] for c in listed.json()] == ["привет"]
    assert [(m["role"], m["content"]) for m in detail.json()["messages"]] == [
        ("user", "привет"),
        ("assistant", "Привет!"),
    ]
    assert foreign.status_code == 404
    assert deleted.status_code == 204
    assert (await client.get("/conversations", headers=headers)).json() == []
