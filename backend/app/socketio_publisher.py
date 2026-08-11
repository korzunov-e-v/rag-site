import socketio

from backend.app.settings import settings


manager = socketio.RedisManager(settings.redis_url)


def emit_document_status(
    document_id: int,
    status: str,
) -> None:
    manager.emit(
        "document:status",
        {
            "document_id": document_id,
            "status": status,
        },
    )
