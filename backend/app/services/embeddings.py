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


async def create_embeddings(texts: list[str]) -> list[list[float]]:
    # Большой документ одним запросом упирается в лимиты провайдера
    # на число входов и токенов, поэтому отправляем пачками.
    embeddings = []
    batch_size = settings.embedding_batch_size

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]

        try:
            response = await client.embeddings.create(
                model=settings.openrouter_embedding_model,
                input=batch,
            )
        except Exception as error:
            if _is_retryable(error):
                raise RetryableError(
                    "Embedding provider temporarily unavailable"
                ) from error
            raise

        data = sorted(response.data, key=lambda result: result.index)
        embeddings.extend(result.embedding for result in data)

    return embeddings
