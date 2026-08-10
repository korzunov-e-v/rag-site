import logging

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # model_config = {"env_file": ".env"}

    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/rag"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672//"

    openrouter_llm_model: str
    openrouter_embedding_model: str
    openrouter_api_key: str
    openrouter_embedding_model_dimensions: int

    max_distance: float

    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
    s3_bucket: str = "documents"

    system_prompt: str = """
    Ты отвечаешь на вопрос пользователя, используя только
предоставленный контекст. Отвечай на русском языке.

Контекст:
{chunks}

...

Вопрос:
{query}"""

settings = Settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)
logger.info(settings.model_dump_json(indent=2))
