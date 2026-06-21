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
    openrouter_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_chat_model: str = "llama-3.1-8b-instant"
    jina_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    llm_provider: str = "auto"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "citemind_chunks"
    retrieval_mode: str = "vector"
    reranker_mode: str = "none"
    reranker_top_k: int = 30
    reranker_final_k: int = 5
    document_parser: str = "markitdown"
    llama_cloud_api_key: Optional[str] = None
    page_index_min_chunks: int = 8
    max_upload_bytes: int = 10_000_000
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
