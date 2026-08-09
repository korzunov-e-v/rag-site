from backend.app.llm.openrouter import client
from backend.app.settings import settings


def create_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model=settings.openrouter_embedding_model,
        input=text,
    )
    embedding = response.data[0].embedding
    return embedding



def create_embeddings(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model=settings.openrouter_embedding_model,
        input=texts,
    )
    embedding = [result.embedding for result in response.data]
    return embedding

