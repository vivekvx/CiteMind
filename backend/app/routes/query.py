from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.db.database import get_db
from backend.app.models.document import Document
from backend.app.models.query_log import QueryLog
from backend.app.schemas.query import QueryCitation, QueryRequest, QueryResponse
from backend.app.services.answer_generator import (
    extract_requested_count,
    generate_answer,
    is_summary_query,
)
from backend.app.services.retriever import retrieve, retrieve_summary_context


router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
def query_documents(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    document_ids = request.document_ids or _latest_document_ids(db)
    records = (
        retrieve_summary_context(
            request.query,
            top_k=extract_requested_count(request.query) + 5,
            document_ids=document_ids,
        )
        if is_summary_query(request.query)
        else retrieve(request.query, document_ids=document_ids)
    )
    answer = generate_answer(request.query, records)

    db.add(QueryLog(query=request.query, answer=answer))
    db.commit()

    citations = [
        QueryCitation(
            document_id=record.document_id,
            chunk_index=record.chunk_index,
            text=record.text,
        )
        for record in records
    ]

    return QueryResponse(answer=answer, citations=citations)


def _latest_document_ids(db: Session) -> Optional[list[int]]:
    latest_document_id = db.scalar(
        select(Document.id).order_by(Document.created_at.desc()).limit(1)
    )
    return [latest_document_id] if latest_document_id is not None else None
