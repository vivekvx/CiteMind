from backend.app.services.embeddings import embed_text
from backend.app.services.vector_store import VectorRecord, vector_store


def retrieve(query: str, top_k: int = 3) -> list[VectorRecord]:
    return vector_store.search(embed_text(query), top_k=top_k)
