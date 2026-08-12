from openai import APIConnectionError, APIStatusError, RateLimitError

from backend.app.exceptions import RetryableError
from backend.app.llm.openrouter import client
from backend.app.settings import settings


def _is_retryable(error: Exception) -> bool:
    if isinstance(error, (APIConnectionError, RateLimitError)):
        return True

    if isinstance(error, APIStatusError):
        return error.status_code >= 500

    return False


async def create_embedding(text: str) -> list[float]:
    try:
        response = await client.embeddings.create(
            model=settings.openrouter_embedding_model,
            input=text,
        )
    except Exception as error:
        if _is_retryable(error):
            raise RetryableError(
                "Embedding provider temporarily unavailable"
            ) from error
        raise

    return response.data[0].embedding


def create_embeddings(texts: list[str]) -> list[list[float]]:
    try:
        response = client.embeddings.create(
            model=settings.openrouter_embedding_model,
            input=texts,
        )
    except Exception as error:
        if _is_retryable(error):
            raise RetryableError(
                "Embedding provider temporarily unavailable"
            ) from error
        raise

    return [result.embedding for result in response.data]
