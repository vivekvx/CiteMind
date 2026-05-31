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
    return LlmProvider(
        api_key=settings.llm_api_key or settings.openai_api_key,
        base_url=settings.llm_base_url or "https://api.openai.com/v1",
        chat_model=settings.llm_chat_model or settings.openai_chat_model,
    )
