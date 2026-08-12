import asyncio
import json
from collections import defaultdict

from backend.app.llm.openrouter import client
from backend.app.services.embeddings import create_embedding
from backend.app.services.retrieval import search_chunks
from backend.app.settings import settings


async def ask_documents(query: str, db):
    query_embedding = await create_embedding(query)

    chunks = search_chunks(
        query_embedding=query_embedding,
        db=db,
        limit=10,
    )

    if not chunks:
        return

    chunks_by_document = defaultdict(list)

    for chunk, distance in chunks:
        chunks_by_document[chunk.document_id].append(
            (chunk, distance)
        )

    tasks = [
        process_document(
            query=query,
            document_id=document_id,
            document_chunks=document_chunks,
        )
        for document_id, document_chunks
        in chunks_by_document.items()
    ]

    for task in asyncio.as_completed(tasks):
        yield await task


async def generate_document_answer(
    query: str,
    document_chunks: list,
):
    document = document_chunks[0][0].document

    context = "\n\n".join(
        f"[Источник {index + 1}]\n{chunk.text}"
        for index, (chunk, _) in enumerate(document_chunks)
    )

    distance = min(
        distance
        for _, distance in document_chunks
    )

    response = await client.chat.completions.create(
        model=settings.openrouter_llm_model,
        messages=[
            {
                "role": "system",
                "content": settings.system_prompt.format(
                    chunks=context,
                    query=query,
                ),
            },
            {
                "role": "user",
                "content": query,
            },
        ],
    )

    response_content = response.choices[0].message.content

    if not response_content:
        raise ValueError("LLM returned empty response")

    print("LLM RESPONSE:")
    print(response_content)

    response_content = response_content.strip()

    if response_content.startswith("```json"):
        response_content = response_content[7:]

    if response_content.endswith("```"):
        response_content = response_content[:-3]

    response_content = response_content.strip()

    response_data = json.loads(response_content)

    answer = response_data["answer"]
    quotes = response_data.get("quotes", [])

    sources = []
    used_texts = set()

    for quote in quotes[:3]:
        for chunk, chunk_distance in document_chunks:
            if chunk.text in used_texts:
                continue

            if quote in chunk.text:
                sources.append(
                    {
                        "chunk_id": chunk.id,
                        "text": chunk.text,
                        "quote": quote,
                        "distance": chunk_distance,
                    }
                )

                used_texts.add(chunk.text)
                break

    sources.sort(
        key=lambda source: source["distance"]
    )

    return {
        "document_id": document.id,
        "filename": document.filename,
        "distance": distance,
        "answer": answer,
        "sources": sources,
    }


async def process_document(
    query: str,
    document_id: int,
    document_chunks: list,
):
    try:
        return await generate_document_answer(
            query,
            document_chunks,
        )

    except Exception as exc:
        print(
            f"DOCUMENT ERROR: "
            f"id={document_id} "
            f"error={exc}"
        )

        return {
            "document_id": document_id,
            "filename": document_chunks[0][0].document.filename,
            "error": str(exc),
        }
