import hashlib
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.database import get_db
from backend.app.models.citation import Citation
from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.eval_result import EvalResult
from backend.app.models.query_log import QueryLog
from backend.app.schemas.document import DocumentListItem, DocumentUploadResponse
from backend.app.services.chunker import chunk_text
from backend.app.services.document_loader import load_document_content
from backend.app.services.embeddings import embed_chunks
from backend.app.services.page_index import build_page_index_tree
from backend.app.services.vector_store import vector_store


router = APIRouter(prefix="/documents", tags=["documents"])
SAMPLE_DOCUMENT_PATH = Path(__file__).resolve().parents[3] / "sample_docs" / "sample_ai_report.md"


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    title = file.filename or "Untitled document"
    content = await file.read()
    return _store_document_content(db, title, content)


@router.post("/demo/reset", response_model=DocumentUploadResponse)
def reset_demo_data(db: Session = Depends(get_db)) -> DocumentUploadResponse:
    if not SAMPLE_DOCUMENT_PATH.exists():
        raise HTTPException(status_code=500, detail="Sample document not found.")

    for model in (EvalResult, QueryLog, Citation, DocumentChunk, Document):
        db.execute(delete(model))
    db.commit()
    vector_store.records = []

    return _store_document_content(
        db,
        SAMPLE_DOCUMENT_PATH.name,
        SAMPLE_DOCUMENT_PATH.read_bytes(),
    )


def _store_document_content(
    db: Session,
    title: str,
    content: bytes,
) -> DocumentUploadResponse:
    content_hash = hashlib.sha256(content).hexdigest()

    existing_document = db.scalar(
        select(Document)
        .where(Document.content_hash == content_hash)
        .order_by(Document.created_at.desc())
    )
    existing_chunks = (
        _document_chunks(db, existing_document.id)
        if existing_document
        else []
    )
    if existing_document and existing_chunks:
        chunk_texts = [chunk.text for chunk in existing_chunks]
        vector_store.add_document(
            existing_document.id,
            chunk_texts,
            _chunk_embeddings(existing_chunks) or embed_chunks(chunk_texts),
        )
        return DocumentUploadResponse(
            id=existing_document.id,
            title=existing_document.title,
            chunks=len(existing_chunks),
        )

    text = load_document_content(content, title)
    chunks = chunk_text(text)
    embeddings = embed_chunks(chunks)
    existing_document = existing_document or _find_document_by_chunks(db, chunks)

    if existing_document:
        document = existing_document
        document.title = document.title or title
        document.abstract = document.abstract or (chunks[0] if chunks else None)
        document.content_hash = content_hash
        db.commit()
        db.refresh(document)
    else:
        document = Document(
            title=title,
            abstract=chunks[0] if chunks else None,
            content_hash=content_hash,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

    document.page_index_tree_json = (
        build_page_index_tree(document.id, chunks)
        if _should_store_page_index_tree(title, chunks)
        else None
    )
    db.commit()
    db.refresh(document)

    _replace_document_chunks(db, document.id, chunks, embeddings)
    vector_store.add_document(document.id, chunks, embeddings)

    return DocumentUploadResponse(
        id=document.id,
        title=document.title,
        chunks=len(chunks),
    )


@router.get("", response_model=list[DocumentListItem])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.created_at.desc())))


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    db.delete(document)
    db.commit()
    vector_store.remove_document(document_id)
    return {"status": "deleted"}


def _document_chunks(db: Session, document_id: int) -> list[DocumentChunk]:
    return list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
    )


def _replace_document_chunks(
    db: Session,
    document_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    for chunk in _document_chunks(db, document_id):
        db.delete(chunk)
    db.add_all(
        DocumentChunk(
            document_id=document_id,
            chunk_index=index,
            text=chunk,
            embedding_json=json.dumps(embeddings[index]),
        )
        for index, chunk in enumerate(chunks)
    )
    db.commit()


def _find_document_by_chunks(db: Session, chunks: list[str]) -> Optional[Document]:
    if not chunks:
        return None

    documents = list(
        db.scalars(
            select(Document)
            .where(Document.content_hash.is_(None))
            .order_by(Document.created_at.desc())
        )
    )
    for document in documents:
        existing_chunks = _document_chunks(db, document.id)
        if [chunk.text for chunk in existing_chunks] == chunks:
            return document
    return None


def _chunk_embeddings(chunks: list[DocumentChunk]) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for chunk in chunks:
        if not chunk.embedding_json:
            return []
        try:
            embeddings.append(json.loads(chunk.embedding_json))
        except json.JSONDecodeError:
            return []
    return embeddings


def _should_store_page_index_tree(title: str, chunks: list[str]) -> bool:
    settings = get_settings()
    if settings.retrieval_mode != "pageindex":
        return False
    if len(chunks) < settings.page_index_min_chunks:
        return False
    return title.lower().endswith((".pdf", ".md", ".markdown", ".txt"))
