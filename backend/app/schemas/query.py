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
    answer: str
    citations: list[QueryCitation]
