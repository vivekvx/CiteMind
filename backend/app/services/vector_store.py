import logging
from dataclasses import dataclass
from math import sqrt
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client import models as qmodels

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

VECTOR_SIZE = 768  # Jina embeddings v2 base
_ID_MULTIPLIER = 100_000


@dataclass
class VectorRecord:
    document_id: int
    chunk_index: int
    text: str
    embedding: list[float]


def _point_id(document_id: int, chunk_index: int) -> int:
    return document_id * _ID_MULTIPLIER + chunk_index


def _to_record(point) -> VectorRecord:
    return VectorRecord(
        document_id=point.payload["document_id"],
        chunk_index=point.payload["chunk_index"],
        text=point.payload["text"],
        embedding=list(point.vector) if point.vector else [],
    )


def _doc_filter(document_id: int) -> qmodels.Filter:
    return qmodels.Filter(
        must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=document_id))]
    )


class QdrantVectorStore:
    def __init__(self) -> None:
        self._client: Optional[QdrantClient] = None

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            settings = get_settings()
            qdrant_url = settings.qdrant_url
            if qdrant_url and qdrant_url != "http://localhost:6333":
                self._client = QdrantClient(url=qdrant_url)
            else:
                self._client = QdrantClient(location=":memory:")
            self._ensure_collection()
        return self._client

    def _ensure_collection(self) -> None:
        settings = get_settings()
        col = settings.qdrant_collection
        existing = {c.name for c in self._client.get_collections().collections}
        if col in existing:
            if self._collection_dim(col) == VECTOR_SIZE:
                return
            logger.warning(
                "Qdrant collection %s has stale vector dim; recreating with dim %d",
                col,
                VECTOR_SIZE,
            )
            self._client.delete_collection(col)
        self._client.create_collection(
            collection_name=col,
            vectors_config=qmodels.VectorParams(size=VECTOR_SIZE, distance=qmodels.Distance.COSINE),
        )

    def _collection_dim(self, col: str) -> Optional[int]:
        try:
            vectors = self._client.get_collection(col).config.params.vectors
            if isinstance(vectors, qmodels.VectorParams):
                return vectors.size
            return None
        except Exception as exc:
            logger.warning("Qdrant collection info failed (%s): %s", col, exc)
            return None

    @property
    def records(self) -> list[VectorRecord]:
        try:
            client = self._get_client()
            col = get_settings().qdrant_collection
            points, _ = client.scroll(collection_name=col, limit=100_000, with_vectors=True)
            result = [_to_record(p) for p in points]
            result.sort(key=lambda r: (r.document_id, r.chunk_index))
            return result
        except Exception as exc:
            logger.warning("Qdrant scroll failed: %s", exc)
            return []

    @records.setter
    def records(self, value: list[VectorRecord]) -> None:
        try:
            client = self._get_client()
            col = get_settings().qdrant_collection
            client.delete_collection(col)
            self._ensure_collection()
            if value:
                self._upsert_records(value)
        except Exception as exc:
            logger.warning("Qdrant records reset failed: %s", exc)

    def _upsert_records(self, records: list[VectorRecord]) -> None:
        client = self._get_client()
        col = get_settings().qdrant_collection
        points = [
            qmodels.PointStruct(
                id=_point_id(r.document_id, r.chunk_index),
                vector=r.embedding,
                payload={"document_id": r.document_id, "chunk_index": r.chunk_index, "text": r.text},
            )
            for r in records
            if len(r.embedding) == VECTOR_SIZE
        ]
        if points:
            client.upsert(collection_name=col, points=points)

    def add_document(
        self,
        document_id: int,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        try:
            client = self._get_client()
            col = get_settings().qdrant_collection
            client.delete(
                collection_name=col,
                points_selector=qmodels.FilterSelector(filter=_doc_filter(document_id)),
            )
            points = [
                qmodels.PointStruct(
                    id=_point_id(document_id, i),
                    vector=emb,
                    payload={"document_id": document_id, "chunk_index": i, "text": chunk},
                )
                for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
                if len(emb) == VECTOR_SIZE
            ]
            if points:
                client.upsert(collection_name=col, points=points)
        except Exception as exc:
            logger.warning("Qdrant add_document failed (doc %d): %s", document_id, exc)

    def document_records(self, document_id: int) -> list[VectorRecord]:
        try:
            client = self._get_client()
            col = get_settings().qdrant_collection
            points, _ = client.scroll(
                collection_name=col,
                scroll_filter=_doc_filter(document_id),
                limit=100_000,
                with_vectors=True,
            )
            result = [_to_record(p) for p in points]
            result.sort(key=lambda r: r.chunk_index)
            return result
        except Exception as exc:
            logger.warning("Qdrant document_records failed (doc %d): %s", document_id, exc)
            return []

    def remove_document(self, document_id: int) -> None:
        try:
            client = self._get_client()
            col = get_settings().qdrant_collection
            client.delete(
                collection_name=col,
                points_selector=qmodels.FilterSelector(filter=_doc_filter(document_id)),
            )
        except Exception as exc:
            logger.warning("Qdrant remove_document failed (doc %d): %s", document_id, exc)

    def search(
        self,
        embedding: list[float],
        top_k: int = 3,
        document_ids: Optional[list[int]] = None,
    ) -> list[VectorRecord]:
        if len(embedding) != VECTOR_SIZE:
            return []
        try:
            client = self._get_client()
            col = get_settings().qdrant_collection
            query_filter = None
            if document_ids:
                query_filter = qmodels.Filter(
                    must=[qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchAny(any=document_ids),
                    )]
                )
            results = client.search(
                collection_name=col,
                query_vector=embedding,
                query_filter=query_filter,
                limit=top_k,
                with_vectors=True,
            )
            return [_to_record(r) for r in results]
        except Exception as exc:
            logger.warning("Qdrant search failed: %s", exc)
            return []

    @staticmethod
    def _similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        ln = sqrt(sum(v * v for v in left))
        rn = sqrt(sum(v * v for v in right))
        if ln == 0 or rn == 0:
            return 0.0
        return dot / (ln * rn)


vector_store = QdrantVectorStore()
