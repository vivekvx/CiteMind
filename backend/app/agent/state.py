from dataclasses import dataclass, field
from typing import Optional

from backend.app.agent.intent import QueryIntent
from backend.app.services.vector_store import VectorRecord


@dataclass
class ResearchAgentState:
    question: str
    document_ids: list[int]
    active_document_id: Optional[int]
    intent: QueryIntent
    requested_count: int
    word_limit: Optional[int] = None
    retrieved_chunks: list[VectorRecord] = field(default_factory=list)
    used_llm: bool = False
