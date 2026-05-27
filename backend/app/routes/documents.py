from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.models.document import Document
from backend.app.schemas.document import DocumentListItem, DocumentUploadResponse
from backend.app.services.chunker import chunk_text
from backend.app.services.document_loader import load_document_text
from backend.app.services.embeddings import embed_chunks
from backend.app.services.vector_store import vector_store


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    text = await load_document_text(file)
    chunks = chunk_text(text)

    document = Document(
        title=file.filename or "Untitled document",
        abstract=chunks[0] if chunks else None,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    vector_store.add_document(document.id, chunks, embed_chunks(chunks))

    return DocumentUploadResponse(
        id=document.id,
        title=document.title,
        chunks=len(chunks),
    )


@router.get("", response_model=list[DocumentListItem])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.created_at.desc())))
