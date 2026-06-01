from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.core.rate_limit import enforce_rate_limit
from backend.app.core.config import get_settings
from backend.app.db.database import get_db, hydrate_vector_store, require_production_database
from backend.app.models.document import Document
from backend.app.models.query_log import QueryLog
from backend.app.schemas.query import QueryCitation, QueryRequest, QueryResponse
from backend.app.agent.planner import run_research_agent
from backend.app.services.answer_generator import generate_answer_result
from backend.app.services.page_index import retrieve_page_index_records


router = APIRouter(prefix="/query", tags=["query"], dependencies=[Depends(enforce_rate_limit)])


@router.post("", response_model=QueryResponse)
def query_documents(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    require_production_database()
    document_ids = request.document_ids or _latest_document_ids(db)
    _ensure_documents_exist(db, document_ids or [])
    result = run_research_agent(request.query, document_ids or [])
    if not result.state.retrieved_chunks and document_ids:
        hydrate_vector_store()
        result = run_research_agent(request.query, document_ids or [])
    records = result.state.retrieved_chunks
    retrieval_strategy = "vector"
    retrieval_comparison = {
        "baseline_chunks": len(records),
        "pageindex_chunks": 0,
    }

    if get_settings().retrieval_mode == "pageindex":
        page_index_records = retrieve_page_index_records(
            db,
            request.query,
            document_ids,
            result.state.intent,
            max(len(records), 5),
        )
        retrieval_comparison["pageindex_chunks"] = len(page_index_records)
        if page_index_records:
            answer, used_llm = generate_answer_result(
                request.query,
                page_index_records,
                result.state.intent,
                result.state.requested_count,
                result.state.word_limit,
            )
            result.answer = answer
            result.state.retrieved_chunks = page_index_records
            result.state.used_llm = used_llm
            records = page_index_records
            retrieval_strategy = "pageindex"

    query_id = _save_query_log(db, request.query, result.answer)

    citations = [
        QueryCitation(
            document_id=record.document_id,
            chunk_index=record.chunk_index,
            text=record.text,
        )
        for record in records
    ]

    return QueryResponse(
        query_id=query_id,
        answer=result.answer,
        citations=citations,
        retrieved_chunks=citations,
        document_ids_used=result.state.document_ids,
        intent=result.state.intent.value,
        requested_count=result.state.requested_count,
        word_limit=result.state.word_limit,
        used_llm=result.state.used_llm,
        retrieved_chunk_count=len(citations),
        retrieval_strategy=retrieval_strategy,
        retrieval_comparison=retrieval_comparison,
    )


def _save_query_log(db: Session, query: str, answer: str) -> int:
    query_log = QueryLog(query=query, answer=answer)
    db.add(query_log)
    try:
        db.commit()
        db.refresh(query_log)
        return query_log.id
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"Query logging skipped: {type(exc).__name__}: {exc}")
        return 0


def _latest_document_ids(db: Session) -> Optional[list[int]]:
    latest_document_id = db.scalar(
        select(Document.id).order_by(Document.created_at.desc()).limit(1)
    )
    return [latest_document_id] if latest_document_id is not None else None


def _ensure_documents_exist(db: Session, document_ids: list[int]) -> None:
    if not document_ids:
        return
    existing_ids = set(
        db.scalars(select(Document.id).where(Document.id.in_(document_ids)))
    )
    missing_ids = [document_id for document_id in document_ids if document_id not in existing_ids]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=(
                "Selected document is no longer available. Upload it again after "
                "persistent storage is configured."
            ),
        )
