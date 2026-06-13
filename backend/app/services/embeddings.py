import logging

import httpx

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
# OpenAI accepts up to 2048 inputs per request; stay well under to keep
# request bodies small for serverless memory limits.
_BATCH_SIZE = 128


def embed_text(text: str) -> list[float]:
    return embed_chunks([text])[0]


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    if not chunks:
        return []
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for embeddings.")

    embeddings: list[list[float]] = []
    with httpx.Client(timeout=60.0) as client:
        for start in range(0, len(chunks), _BATCH_SIZE):
            batch = chunks[start : start + _BATCH_SIZE]
            response = client.post(
                _OPENAI_EMBEDDINGS_URL,
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"model": settings.openai_embedding_model, "input": batch},
            )
            response.raise_for_status()
            data = sorted(response.json()["data"], key=lambda item: item["index"])
            embeddings.extend(item["embedding"] for item in data)
    return embeddings
