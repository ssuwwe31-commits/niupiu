from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_drama"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    LLM_MODEL: str = "qwen2.5:7b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
