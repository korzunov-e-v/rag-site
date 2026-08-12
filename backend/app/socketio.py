import socketio

from backend.app.db.connect import SessionLocal
from backend.app.settings import settings
import asyncio

from backend.app.services.ask import ask_documents

manager = socketio.AsyncRedisManager(settings.redis_url)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    client_manager=manager,
)


async def emit_document_status(
    document_id: int,
    status: str,
) -> None:
    print(
        f"SOCKET.IO EMIT: "
        f"document:status "
        f"id={document_id} "
        f"status={status}"
    )
    await sio.emit(
        "document:status",
        {
            "document_id": document_id,
            "status": status,
        },
    )


@sio.event
async def ask(sid, data):
    query = data["query"]

    await sio.emit(
        "ask:started",
        {},
        to=sid,
    )

    db = SessionLocal()

    try:
        async for answer in ask_documents(query, db):
            await sio.emit(
                "answer",
                answer,
                to=sid,
            )

        await sio.emit(
            "ask:finished",
            {},
            to=sid,
        )

    except Exception as exc:
        print(f"ASK ERROR: {exc}")

        await sio.emit(
            "ask:error",
            {
                "message": "Не удалось выполнить поиск",
            },
            to=sid,
        )

    finally:
        db.close()
