from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.models.query_log import QueryLog
from backend.app.schemas.query import QueryCitation, QueryRequest, QueryResponse
from backend.app.services.answer_generator import generate_answer
from backend.app.services.retriever import retrieve


router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
def query_documents(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    records = retrieve(request.query)
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
