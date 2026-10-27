import logging

import socketio
import jwt

from backend.app.db.models import User
from backend.app.db.connect import SessionLocal
from backend.app.settings import settings
from backend.app.services.chat import handle_ask
from backend.app.socketio_publisher import user_room

logger = logging.getLogger(__name__)

connected_users: dict[str, int] = {}

manager = socketio.AsyncRedisManager(
    settings.redis_url
)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    client_manager=manager,
)


@sio.event
async def ask(sid, data):
    user_id = connected_users.get(sid)

    if user_id is None:
        await sio.emit(
            "ask:error",
            {
                "message": "Необходима авторизация",
            },
            to=sid,
        )
        return

    query = data["query"]
    conversation_id = data.get("conversation_id")

    logger.info("Ask: sid=%s user=%s query=%r", sid, user_id, query)

    async def emit(event: str, payload: dict) -> None:
        await sio.emit(event, payload, to=sid)

    try:
        async with SessionLocal() as db:
            await handle_ask(db, user_id, query, conversation_id, emit)

    except Exception:
        logger.exception("Ask failed: sid=%s", sid)

        await sio.emit(
            "ask:error",
            {
                "message": "Не удалось выполнить поиск",
            },
            to=sid,
        )


@sio.event
async def connect(sid, environ, auth):
    if not auth:
        return False

    token = auth.get("token")

    if not token:
        return False

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )

        user_id = int(payload["sub"])

    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return False

    async with SessionLocal() as db:
        user = await db.get(User, user_id)

    if user is None:
        return False

    connected_users[sid] = user.id
    await sio.enter_room(sid, user_room(user.id))

    logger.info("Socket connected: sid=%s user=%s", sid, user.id)


@sio.event
async def disconnect(sid):
    connected_users.pop(sid, None)
