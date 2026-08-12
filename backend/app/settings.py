import logging

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env"}

    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/rag"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672//"

    openrouter_llm_model: str
    openrouter_embedding_model: str
    openrouter_api_key: SecretStr
    openrouter_embedding_model_dimensions: int

    max_distance: float

    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minio"
    s3_secret_key: SecretStr = "minio123"
    s3_bucket: str = "documents"

    redis_url: str = "redis://redis:6379/0"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    system_prompt: str = """
    Ты отвечаешь на вопрос пользователя, используя только предоставленный контекст.

    Верни JSON строго такого вида:

    {{
      "answer": "ответ на вопрос",
      "quotes": [
        "дословная цитата из контекста"
      ]
    }}

    Правила:
    - answer — ответ пользователю на русском языке.
    - quotes — 1-3 наиболее важных дословных фрагмента из контекста.
    - Цитаты должны полностью и дословно присутствовать в предоставленном контексте.
    - Не изменяй слова, окончания, знаки препинания внутри цитат.
    - Не придумывай цитаты.

    Контекст:
    {chunks}

    ...

    Вопрос:
    {query}
    """
settings = Settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)
logger.info(settings.model_dump_json(indent=2))
