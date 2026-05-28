from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.db.database import get_db
from backend.app.models.document import Document
from backend.app.models.query_log import QueryLog
from backend.app.schemas.query import QueryCitation, QueryRequest, QueryResponse
from backend.app.agent.planner import run_research_agent


router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
def query_documents(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    document_ids = request.document_ids or _latest_document_ids(db)
    result = run_research_agent(request.query, document_ids or [])
    records = result.state.retrieved_chunks

    query_log = QueryLog(query=request.query, answer=result.answer)
    db.add(query_log)
    db.commit()
    db.refresh(query_log)

    citations = [
        QueryCitation(
            document_id=record.document_id,
            chunk_index=record.chunk_index,
            text=record.text,
        )
        for record in records
    ]

    return QueryResponse(
        query_id=query_log.id,
        answer=result.answer,
        citations=citations,
        retrieved_chunks=citations,
        document_ids_used=result.state.document_ids,
        intent=result.state.intent.value,
        requested_count=result.state.requested_count,
        used_llm=result.state.used_llm,
        retrieved_chunk_count=len(citations),
    )


def _latest_document_ids(db: Session) -> Optional[list[int]]:
    latest_document_id = db.scalar(
        select(Document.id).order_by(Document.created_at.desc()).limit(1)
    )
    return [latest_document_id] if latest_document_id is not None else None
