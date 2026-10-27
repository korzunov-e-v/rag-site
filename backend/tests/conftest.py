import hashlib
import math
import os
import re
from io import BytesIO
from pathlib import Path

# Тесты работают с отдельной базой, чтобы не трогать данные разработки.
# Переменную нужно выставить до импорта приложения: settings читаются при импорте.
_base_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@db:5432/rag",
)
TEST_DATABASE_URL = _base_url.rsplit("/", 1)[0] + "/rag_test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import psycopg2  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from backend.app.db.connect import SessionLocal, engine  # noqa: E402
from backend.app.main import fastapi_app  # noqa: E402
from backend.app.settings import settings  # noqa: E402

PASSWORD = "Secret12345!"


def _create_test_database() -> None:
    url = TEST_DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    server_url, name = url.rsplit("/", 1)

    connection = psycopg2.connect(f"{server_url}/postgres")
    connection.autocommit = True

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
        if cursor.fetchone() is None:
            cursor.execute(f'CREATE DATABASE "{name}"')

    connection.close()


@pytest.fixture(scope="session", autouse=True)
def database():
    _create_test_database()

    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    command.upgrade(Config(str(alembic_ini)), "head")


@pytest.fixture(autouse=True)
async def clean_database():
    yield

    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE users, documents, document_chunks RESTART IDENTITY CASCADE"))

    # Каждый тест идёт в своём event loop, а соединения пула привязаны к loop.
    await engine.dispose()


@pytest.fixture
async def db():
    async with SessionLocal() as session:
        yield session


def fake_embedding(value: str) -> list[float]:
    """Детерминированный «эмбеддинг»: мешок слов, разложенный хешами по измерениям.

    Тексты с общими словами получаются близкими по косинусу, как у настоящей модели.
    """
    dimensions = settings.openrouter_embedding_model_dimensions
    vector = [0.0] * dimensions

    for word in re.findall(r"\w+", value.lower()):
        index = int(hashlib.md5(word.encode()).hexdigest(), 16) % dimensions
        vector[index] += 1.0

    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    async def create_embedding(value: str) -> list[float]:
        return fake_embedding(value)

    async def create_embeddings(values: list[str]) -> list[list[float]]:
        return [fake_embedding(value) for value in values]

    monkeypatch.setattr("backend.app.services.search.create_embedding", create_embedding)
    monkeypatch.setattr("backend.app.services.ask.create_embedding", create_embedding)
    monkeypatch.setattr("backend.app.services.process_doc.create_embeddings", create_embeddings)


class FakeStorage:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    def upload(self, file, key: str) -> None:
        self.files[key] = file.read()

    def delete(self, key: str) -> None:
        self.files.pop(key, None)

    def download(self, key: str) -> BytesIO:
        return BytesIO(self.files[key])


@pytest.fixture(autouse=True)
def storage(monkeypatch):
    fake = FakeStorage()

    for module in ("save", "process_doc"):
        monkeypatch.setattr(f"backend.app.services.{module}.s3_storage", fake)
    monkeypatch.setattr("backend.app.api.v1.api.documents.s3_storage", fake)

    return fake


@pytest.fixture(autouse=True)
def emitted(monkeypatch):
    events = []

    monkeypatch.setattr(
        "backend.app.tasks.documents.emit_document_status",
        lambda *args: events.append(args),
    )

    return events


@pytest.fixture(autouse=True)
def queued(monkeypatch):
    document_ids = []

    monkeypatch.setattr(
        "backend.app.api.v1.api.documents.process_document.delay",
        document_ids.append,
    )

    return document_ids


@pytest.fixture
async def client():
    transport = ASGITransport(app=fastapi_app)

    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as client:
        yield client


async def register(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def auth_headers(client: AsyncClient, email: str = "user@example.com") -> dict:
    tokens = await register(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}
