import socketio

from backend.app.settings import settings


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
