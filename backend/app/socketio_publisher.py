import socketio

from backend.app.settings import settings


manager = socketio.RedisManager(settings.redis_url)


def user_room(user_id: int) -> str:
    return f"user:{user_id}"


def emit_document_status(
    document_id: int,
    status: str,
    owner_id: int,
) -> None:
    print(
        "REDIS SOCKET EMIT:",
        document_id,
        status,
        settings.redis_url,
    )
    manager.emit(
        "document:status",
        {
            "document_id": document_id,
            "status": status,
        },
        room=user_room(owner_id),
    )
