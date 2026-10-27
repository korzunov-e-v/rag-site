from openai import AsyncOpenAI

from backend.app.settings import settings

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key.get_secret_value(),
    # Общий пул бесплатных/дешёвых моделей часто отвечает 429 — повторяем
    # с экспоненциальной задержкой (по умолчанию повторов всего 2).
    max_retries=5,
)
