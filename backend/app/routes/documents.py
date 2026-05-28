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
    title = file.filename or "Untitled document"
    existing_document = db.scalar(
        select(Document).where(Document.title == title).order_by(Document.created_at.desc())
    )
    existing_records = (
        vector_store.document_records(existing_document.id)
        if existing_document
        else []
    )
    if existing_document and existing_records:
        return DocumentUploadResponse(
            id=existing_document.id,
            title=existing_document.title,
            chunks=len(existing_records),
        )

    text = await load_document_text(file)
    chunks = chunk_text(text)

    if existing_document:
        document = existing_document
        if not document.abstract and chunks:
            document.abstract = chunks[0]
            db.commit()
            db.refresh(document)
    else:
        document = Document(
            title=title,
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
