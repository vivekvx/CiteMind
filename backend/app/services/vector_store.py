from dataclasses import dataclass, field
from math import sqrt


@dataclass
class VectorRecord:
    document_id: int
    chunk_index: int
    text: str
    embedding: list[float]


@dataclass
class InMemoryVectorStore:
    records: list[VectorRecord] = field(default_factory=list)

    def add_document(
        self,
        document_id: int,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        for index, chunk in enumerate(chunks):
            self.records.append(
                VectorRecord(
                    document_id=document_id,
                    chunk_index=index,
                    text=chunk,
                    embedding=embeddings[index],
                )
            )

    def search(self, embedding: list[float], top_k: int = 3) -> list[VectorRecord]:
        scored = [
            (self._similarity(embedding, record.embedding), record)
            for record in self.records
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:top_k]]

    @staticmethod
    def _similarity(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0
        return numerator / (left_norm * right_norm)


vector_store = InMemoryVectorStore()
