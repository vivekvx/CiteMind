import json
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings


settings = get_settings()

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from backend.app.models import Base

    Base.metadata.create_all(bind=engine)
    _ensure_local_schema()
    hydrate_vector_store()


def _ensure_local_schema() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "documents" in table_names:
        document_columns = {column["name"] for column in inspector.get_columns("documents")}
        if "content_hash" not in document_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE documents ADD COLUMN content_hash VARCHAR(64)"))
                connection.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_documents_content_hash ON documents (content_hash)")
                )

    if "document_chunks" in table_names:
        chunk_columns = {column["name"] for column in inspector.get_columns("document_chunks")}
        if "embedding_json" not in chunk_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE document_chunks ADD COLUMN embedding_json TEXT"))


def hydrate_vector_store() -> None:
    from backend.app.models.document_chunk import DocumentChunk
    from backend.app.services.embeddings import embed_chunks
    from backend.app.services.vector_store import vector_store

    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(DocumentChunk).order_by(
                    DocumentChunk.document_id,
                    DocumentChunk.chunk_index,
                )
            )
        )

    chunks_by_document: dict[int, list[str]] = {}
    embeddings_by_document: dict[int, list[list[float]]] = {}
    for row in rows:
        chunks_by_document.setdefault(row.document_id, []).append(row.text)
        if row.embedding_json:
            try:
                embeddings_by_document.setdefault(row.document_id, []).append(
                    json.loads(row.embedding_json)
                )
            except json.JSONDecodeError:
                embeddings_by_document.pop(row.document_id, None)

    for document_id, chunks in chunks_by_document.items():
        stored_embeddings = embeddings_by_document.get(document_id, [])
        embeddings = (
            stored_embeddings
            if len(stored_embeddings) == len(chunks)
            else embed_chunks(chunks)
        )
        vector_store.add_document(document_id, chunks, embeddings)
