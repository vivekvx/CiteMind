import re
from typing import Optional

from backend.app.services.embeddings import embed_text
from backend.app.services.vector_store import VectorRecord, vector_store


NOISE_TERMS = (
    "copyright",
    "all rights reserved",
    "isbn",
    "publisher address",
    "contact us",
    "praise for",
    "acknowledgements",
    "acknowledgments",
)


def retrieve(
    query: str,
    top_k: int = 3,
    document_ids: Optional[list[int]] = None,
) -> list[VectorRecord]:
    return vector_store.search(embed_text(query), top_k=top_k, document_ids=document_ids)


def retrieve_summary_context(
    query: str,
    top_k: int = 10,
    document_ids: Optional[list[int]] = None,
) -> list[VectorRecord]:
    semantic_records = retrieve(
        query,
        top_k=max(top_k * 2, 20),
        document_ids=document_ids,
    )
    if not semantic_records:
        return semantic_records

    allowed_document_ids = set(document_ids or [semantic_records[0].document_id])
    clean_records = [
        record
        for record in sorted(vector_store.records, key=lambda item: item.chunk_index)
        if record.document_id in allowed_document_ids and not is_noisy_chunk(record.text)
    ]
    if not clean_records:
        return semantic_records[:top_k]

    selected: dict[tuple[int, int], VectorRecord] = {}
    merged: list[VectorRecord] = []

    for record in clean_records:
        if record.chunk_index > 25:
            continue
        _add_record(record, selected, merged)
        if len(merged) >= min(5, top_k):
            break

    diverse_target = min(top_k, len(merged) + 3)
    if len(merged) < diverse_target:
        step = max(1, len(clean_records) // max(diverse_target - len(merged), 1))
        for record in clean_records[::step]:
            _add_record(record, selected, merged)
            if len(merged) >= diverse_target:
                break

    for record in semantic_records:
        if record.document_id in allowed_document_ids and not is_noisy_chunk(record.text):
            _add_record(record, selected, merged)
        if len(merged) >= top_k:
            break

    return merged[:top_k]


def is_noisy_chunk(text: str) -> bool:
    normalized = " ".join(text.split())
    lower = normalized.lower()
    if len(normalized) < 80:
        return True
    if any(term in lower for term in NOISE_TERMS):
        return True
    if lower in {"index", "table of contents", "contents"}:
        return True
    if lower.startswith(("index ", "table of contents", "contents ")):
        return True

    alpha_count = sum(character.isalpha() for character in normalized)
    alpha_ratio = alpha_count / max(len(normalized), 1)
    if alpha_ratio < 0.45:
        return True

    url_count = len(re.findall(r"https?://|www\.|@\w+", lower))
    if url_count >= 2:
        return True

    symbol_count = len(re.findall(r"[{}[\]();=<>|]{1}", normalized))
    if symbol_count / max(len(normalized), 1) > 0.12:
        return True

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        code_like_lines = [
            line
            for line in lines
            if re.search(r"^(def|class|import|from|for|while|if|return)\b|[{};=<>]", line)
        ]
        if len(code_like_lines) / len(lines) > 0.5:
            return True

    return False


def _add_record(
    record: VectorRecord,
    selected: dict[tuple[int, int], VectorRecord],
    merged: list[VectorRecord],
) -> None:
    key = (record.document_id, record.chunk_index)
    if key not in selected:
        merged.append(record)
        selected[key] = record
