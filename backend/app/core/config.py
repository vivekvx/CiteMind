from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CiteMind API"
    environment: str = "development"
    database_url: str = "sqlite:///./citemind.db"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_chat_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "citemind_chunks"
    retrieval_mode: str = "vector"
    page_index_min_chunks: int = 8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
