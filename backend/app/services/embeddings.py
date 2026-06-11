import logging

logger = logging.getLogger(__name__)
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading BGE-M3 embedding model (first load may take a minute)...")
        _model = SentenceTransformer("BAAI/bge-m3")
        logger.info("BGE-M3 loaded.")
    return _model


def embed_text(text: str) -> list[float]:
    return embed_chunks([text])[0]


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    if not chunks:
        return []
    return _get_model().encode(chunks, normalize_embeddings=True, batch_size=32).tolist()
