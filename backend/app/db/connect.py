from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.settings import settings

engine = create_async_engine(
    settings.async_database_url,
    connect_args={
        "server_settings": {
            # Без iterative scan HNSW отдаёт ef_search ближайших векторов всех
            # пользователей, и фильтр по владельцу может оставить пустой результат.
            "hnsw.iterative_scan": "strict_order",
        },
    },
)
SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as db:
        yield db
