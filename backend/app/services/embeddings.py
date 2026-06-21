import logging

import httpx

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_JINA_EMBEDDINGS_URL = "https://api.jina.ai/v1/embeddings"
_BATCH_SIZE = 64


def embed_text(text: str) -> list[float]:
    return embed_chunks([text])[0]


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    if not chunks:
        return []
    settings = get_settings()
    api_key = settings.jina_api_key
    if not api_key:
        raise RuntimeError("JINA_API_KEY is required for embeddings.")

    embeddings: list[list[float]] = []
    with httpx.Client(timeout=60.0) as client:
        for start in range(0, len(chunks), _BATCH_SIZE):
            batch = chunks[start : start + _BATCH_SIZE]
            response = client.post(
                _JINA_EMBEDDINGS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "jina-embeddings-v2-base-en", "input": batch},
            )
            response.raise_for_status()
            data = sorted(response.json()["data"], key=lambda item: item["index"])
            embeddings.extend(item["embedding"] for item in data)
    return embeddings
