from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env"}

    openrouter_llm_model: str = "llama2"
    openrouter_embedding_model: str = "openai/text-embedding-3-small"
    openrouter_api_key: str
    openrouter_embedding_model_dimensions: int = 1536

    max_distance: float = 0.7

    system_prompt: str = """
    Ты отвечаешь на вопрос пользователя, используя только
предоставленный контекст. Отвечай на русском языке.

Контекст:
{chunks}

...

Вопрос:
{query}"""

settings = Settings()
