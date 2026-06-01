from typing import Optional

from backend.app.core.config import get_settings
from backend.app.services.vector_store import VectorRecord


_FLASHRANK_RANKER: Optional["FlashRankReranker"] = None


class FlashRankReranker:
    def __init__(self) -> None:
        from flashrank import Ranker

        self._ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")

    def rerank(
        self,
        query: str,
        records: list[VectorRecord],
        top_n: int,
    ) -> list[VectorRecord]:
        from flashrank import RerankRequest

        record_by_id = {str(index): record for index, record in enumerate(records)}
        passages = [
            {
                "id": record_id,
                "text": record.text,
                "meta": {
                    "document_id": record.document_id,
                    "chunk_index": record.chunk_index,
                },
            }
            for record_id, record in record_by_id.items()
        ]
        results = self._ranker.rerank(RerankRequest(query=query, passages=passages))
        ranked_records = [
            record_by_id[str(result["id"])]
            for result in results
            if str(result.get("id")) in record_by_id
        ]
        return ranked_records[:top_n]


def rerank_with_optional_flashrank(
    query: str,
    records: list[VectorRecord],
    top_n: int,
) -> tuple[list[VectorRecord], dict[str, object]]:
    metadata: dict[str, object] = {
        "strategy": "vector",
        "reranker_input_chunks": len(records),
        "reranked_chunks": 0,
    }
    if get_settings().reranker_mode != "flashrank" or not records:
        return records[:top_n], metadata

    ranker = _get_flashrank_ranker()
    if ranker is None:
        print("FlashRank reranker unavailable; falling back to vector ordering.")
        return records[:top_n], metadata

    try:
        reranked = ranker.rerank(query, records, top_n)
    except Exception as exc:
        print(f"FlashRank reranking failed: {type(exc).__name__}: {exc}")
        return records[:top_n], metadata

    metadata["strategy"] = "flashrank"
    metadata["reranked_chunks"] = len(reranked)
    return reranked, metadata


def _get_flashrank_ranker() -> Optional[FlashRankReranker]:
    global _FLASHRANK_RANKER
    if _FLASHRANK_RANKER is not None:
        return _FLASHRANK_RANKER
    try:
        _FLASHRANK_RANKER = FlashRankReranker()
    except ImportError:
        return None
    return _FLASHRANK_RANKER
