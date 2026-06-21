from dataclasses import dataclass
from typing import Optional

from backend.app.core.config import get_settings


@dataclass
class LlmProvider:
    api_key: Optional[str]
    base_url: str
    chat_model: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"


def get_llm_provider() -> LlmProvider:
    settings = get_settings()

    # If generic LLM_* env vars are set, use them as highest priority
    if settings.llm_api_key:
        return LlmProvider(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or "https://api.openai.com/v1",
            chat_model=settings.llm_chat_model or "gpt-4o-mini",
        )

    # Next check Groq
    if settings.groq_api_key:
        return LlmProvider(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            chat_model=settings.groq_chat_model,
        )

    # Next check OpenRouter
    if settings.openrouter_api_key:
        return LlmProvider(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            chat_model=settings.llm_chat_model or "openai/gpt-4o-mini",
        )

    # Fallback to OpenAI
    return LlmProvider(
        api_key=settings.openai_api_key,
        base_url=settings.llm_base_url or "https://api.openai.com/v1",
        chat_model=settings.openai_chat_model,
    )
