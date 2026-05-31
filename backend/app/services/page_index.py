import json
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.document import Document
from backend.app.services.embeddings import embed_chunks
from backend.app.services.retriever import keyword_score, rerank_chunks
from backend.app.services.vector_store import VectorRecord


def build_page_index_tree(document_id: int, chunks: list[str]) -> str:
    tree = {
        "document_id": document_id,
        "kind": "pageindex-lite",
        "nodes": [
            {
                "chunk_index": index,
                "title": _node_title(chunk),
                "text": chunk,
            }
            for index, chunk in enumerate(chunks)
        ],
    }
    return json.dumps(tree)


def retrieve_page_index_records(
    db: Session,
    question: str,
    document_ids: Optional[list[int]],
    intent,
    top_k: int,
) -> list[VectorRecord]:
    documents = list(
        db.scalars(
            select(Document)
            .where(Document.id.in_(document_ids or []))
            .where(Document.page_index_tree_json.is_not(None))
        )
    )
    records: list[VectorRecord] = []
    for document in documents:
        records.extend(_records_from_tree(document, question))
    if not records:
        return []
    return rerank_chunks(question, records, intent)[:top_k]


def _records_from_tree(document: Document, question: str) -> list[VectorRecord]:
    try:
        tree = json.loads(document.page_index_tree_json or "{}")
    except json.JSONDecodeError:
        return []

    nodes = tree.get("nodes", [])
    scored_nodes = [
        (keyword_score(question, f"{node.get('title', '')} {node.get('text', '')}"), node)
        for node in nodes
        if isinstance(node, dict) and node.get("text")
    ]
    scored_nodes.sort(key=lambda item: item[0], reverse=True)
    selected = [node for _, node in scored_nodes[:12]]
    texts = [str(node["text"]) for node in selected]
    embeddings = embed_chunks(texts)
    return [
        VectorRecord(
            document_id=document.id,
            chunk_index=int(node.get("chunk_index", index)),
            text=texts[index],
            embedding=embeddings[index],
        )
        for index, node in enumerate(selected)
    ]


def _node_title(text: str) -> str:
    normalized = " ".join(text.split())
    sentence = re.split(r"(?<=[.!?])\s+", normalized)[0]
    return sentence[:120]
