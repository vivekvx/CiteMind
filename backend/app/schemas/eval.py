from pydantic import BaseModel

from backend.app.schemas.query import QueryCitation


class EvalRunRequest(BaseModel):
    query: str
    answer: str
    contexts: list[str] = []
    citations: list[QueryCitation] = []


class EvalRunResponse(BaseModel):
    id: int
    faithfulness_score: float
    answer_relevance_score: float
    context_relevance_score: float
    citation_coverage_score: float
