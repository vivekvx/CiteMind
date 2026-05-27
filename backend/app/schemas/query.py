from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str


class QueryCitation(BaseModel):
    document_id: int
    chunk_index: int
    text: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[QueryCitation]
