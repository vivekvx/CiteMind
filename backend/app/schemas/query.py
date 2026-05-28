from typing import Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    document_ids: Optional[list[int]] = None


class QueryCitation(BaseModel):
    document_id: int
    chunk_index: int
    text: str


class QueryResponse(BaseModel):
    query_id: int
    answer: str
    citations: list[QueryCitation]
    retrieved_chunks: list[QueryCitation] = []
    document_ids_used: list[int] = []
    intent: str = "normal_qa"
    requested_count: int = 10
    used_llm: bool = False
    retrieved_chunk_count: int = 0
