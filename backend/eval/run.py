"""Оценка качества поиска.

Индексирует корпус из eval/corpus с разными размерами чанков и для каждого
вопроса из eval/questions.json проверяет, попал ли ожидаемый фрагмент в top-k.

    docker compose exec app uv run python -m backend.eval.run
    docker compose exec app uv run python -m backend.eval.run --chunk-sizes 128,256 --k 3

Работает с отдельной базой rag_eval. Эмбеддинги настоящие (OpenRouter) и
кешируются в eval/.cache, поэтому повторные прогоны почти бесплатны.
"""
import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR.parents[1]))

_base_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@db:5432/rag",
)
EVAL_DATABASE_URL = _base_url.rsplit("/", 1)[0] + "/rag_eval"
os.environ["DATABASE_URL"] = EVAL_DATABASE_URL

import psycopg2  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from llama_index.core.node_parser import SentenceSplitter  # noqa: E402
from sqlalchemy import text  # noqa: E402

from backend.app.db.connect import SessionLocal, engine  # noqa: E402
from backend.app.db.enums import DocumentStatus  # noqa: E402
from backend.app.db.models import Document, DocumentChunk, User  # noqa: E402
from backend.app.services import embeddings  # noqa: E402
from backend.app.services.retrieval import search_chunks, vector_search  # noqa: E402

CACHE_PATH = EVAL_DIR / ".cache" / "embeddings.json"


class EmbeddingCache:
    def __init__(self, path: Path):
        self.path = path
        self.items: dict[str, list[float]] = (
            json.loads(path.read_text()) if path.exists() else {}
        )

    @staticmethod
    def key(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    async def embed(self, values: list[str]) -> list[list[float]]:
        missing = [value for value in values if self.key(value) not in self.items]

        if missing:
            for value, vector in zip(missing, await embeddings.create_embeddings(missing)):
                self.items[self.key(value)] = vector

            self.path.parent.mkdir(exist_ok=True)
            self.path.write_text(json.dumps(self.items))

        return [self.items[self.key(value)] for value in values]


def normalize(value: str) -> str:
    return " ".join(value.split())


def create_database() -> None:
    url = EVAL_DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    server_url, name = url.rsplit("/", 1)

    connection = psycopg2.connect(f"{server_url}/postgres")
    connection.autocommit = True

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
        if cursor.fetchone() is None:
            cursor.execute(f'CREATE DATABASE "{name}"')

    connection.close()
    command.upgrade(Config(str(EVAL_DIR.parents[1] / "alembic.ini")), "head")


async def index_corpus(
    corpus: dict[str, str],
    chunk_size: int,
    chunk_overlap: int,
    cache: EmbeddingCache,
) -> int:
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE users, documents, document_chunks RESTART IDENTITY CASCADE"))

    async with SessionLocal() as db:
        user = User(email="eval@example.com", password_hash="-")
        db.add(user)
        await db.flush()

        for filename, content in corpus.items():
            document = Document(
                owner_id=user.id,
                filename=filename,
                storage_key="-",
                status=DocumentStatus.PROCESSED,
            )
            db.add(document)
            await db.flush()

            chunks = splitter.split_text(normalize(content))
            vectors = await cache.embed(chunks)

            for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
                db.add(DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    text=chunk,
                    embedding=vector,
                ))

        await db.commit()
        return user.id


async def evaluate(
    questions: list[dict],
    user_id: int,
    k: int,
    cache: EmbeddingCache,
) -> dict[str, dict]:
    vectors = await cache.embed([item["question"] for item in questions])
    results = {"hybrid": [], "vector": []}

    async with SessionLocal() as db:
        for item, vector in zip(questions, vectors):
            found = {
                "hybrid": await search_chunks(item["question"], vector, db, user_id, limit=k),
                "vector": await vector_search(vector, db, user_id, limit=k),
            }

            for method, chunks in found.items():
                rank = next(
                    (
                        position
                        for position, (chunk, _) in enumerate(chunks, start=1)
                        if normalize(item["expected"]) in chunk.text
                    ),
                    None,
                )
                results[method].append(rank)

    return {
        method: {
            "hit": sum(rank is not None for rank in ranks) / len(ranks),
            "mrr": sum(1 / rank for rank in ranks if rank) / len(ranks),
            "missed": [
                item["question"]
                for item, rank in zip(questions, ranks)
                if rank is None
            ],
        }
        for method, ranks in results.items()
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chunk-sizes", default="128,256,500,1000")
    parser.add_argument("--overlap-ratio", type=float, default=0.1)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--verbose", action="store_true", help="показать пропущенные вопросы")
    args = parser.parse_args()

    corpus = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted((EVAL_DIR / "corpus").glob("*.txt"))
    }
    questions = json.loads((EVAL_DIR / "questions.json").read_text(encoding="utf-8"))

    corpus_text = normalize(" ".join(corpus.values()))
    for item in questions:
        assert normalize(item["expected"]) in corpus_text, f"Нет в корпусе: {item['expected']}"

    create_database()
    cache = EmbeddingCache(CACHE_PATH)

    print(f"{len(questions)} вопросов, top-{args.k}\n")
    print(f"{'chunk_size':>10} {'чанков':>7} {'hybrid hit':>11} {'hybrid MRR':>11} {'vector hit':>11} {'vector MRR':>11}")

    for chunk_size in map(int, args.chunk_sizes.split(",")):
        overlap = int(chunk_size * args.overlap_ratio)
        user_id = await index_corpus(corpus, chunk_size, overlap, cache)

        async with SessionLocal() as db:
            chunk_count = await db.scalar(text("SELECT count(*) FROM document_chunks"))

        metrics = await evaluate(questions, user_id, args.k, cache)
        hybrid, vector = metrics["hybrid"], metrics["vector"]

        print(
            f"{chunk_size:>10} {chunk_count:>7} "
            f"{hybrid['hit']:>11.0%} {hybrid['mrr']:>11.2f} "
            f"{vector['hit']:>11.0%} {vector['mrr']:>11.2f}"
        )

        if args.verbose:
            for method in ("hybrid", "vector"):
                for question in metrics[method]["missed"]:
                    print(f"{'':>10} промах {method}: {question}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
