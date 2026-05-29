import re
from typing import Optional

from backend.app.agent.intent import QueryIntent
from backend.app.services.embeddings import embed_text
from backend.app.services.vector_store import VectorRecord, vector_store


NOISE_TERMS = (
    "all rights reserved",
    "acknowledgements",
    "acknowledgments",
    "contact us",
    "copyright",
    "disclaimer",
    "errata",
    "isbn",
    "liability",
    "oreilly.com",
    "permissions",
    "praise for",
    "publisher",
    "publisher address",
    "registered trademarks",
    "trademarks",
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "give",
    "how",
    "important",
    "in",
    "is",
    "it",
    "make",
    "me",
    "of",
    "on",
    "or",
    "pdf",
    "points",
    "study",
    "the",
    "this",
    "to",
    "topics",
    "what",
    "with",
}

CONCEPT_TERMS = {
    "agent",
    "architecture",
    "concept",
    "deployment",
    "evaluation",
    "introduction",
    "monitoring",
    "overview",
    "retrieval",
    "security",
    "tool",
    "workflow",
}


def retrieve(
    query: str,
    top_k: int = 3,
    document_ids: Optional[list[int]] = None,
) -> list[VectorRecord]:
    return vector_store.search(embed_text(query), top_k=top_k, document_ids=document_ids)


def retrieve_context_for_intent(
    question: str,
    document_ids: Optional[list[int]],
    intent: QueryIntent,
    requested_count: int,
) -> list[VectorRecord]:
    if intent in {
        QueryIntent.SUMMARY,
        QueryIntent.IMPORTANT_POINTS,
        QueryIntent.TOPICS,
        QueryIntent.STUDY_NOTES,
        QueryIntent.FLASHCARDS,
        QueryIntent.EXPLANATION,
    }:
        return retrieve_summary_context(document_ids, question, requested_count, intent)

    top_k = 8 if intent == QueryIntent.COMPARISON else 5
    records = retrieve(question, top_k=top_k * 2, document_ids=document_ids)
    clean_records = [record for record in records if not is_noisy_chunk(record.text)]
    return rerank_chunks(question, clean_records or records, intent)[:top_k]


def retrieve_summary_context(
    document_ids: Optional[list[int]],
    question: str,
    requested_count: int = 10,
    intent: QueryIntent = QueryIntent.SUMMARY,
) -> list[VectorRecord]:
    max_chunks = min(18, max(12, requested_count + 6))
    semantic_records = retrieve(
        question,
        top_k=max(max_chunks * 2, 24),
        document_ids=document_ids,
    )
    allowed_document_ids = set(document_ids or [])
    if not allowed_document_ids and semantic_records:
        allowed_document_ids.add(semantic_records[0].document_id)

    document_records = [
        record
        for document_id in allowed_document_ids
        for record in vector_store.document_records(document_id)
    ]
    if not semantic_records and not document_records:
        return []

    clean_records = [
        record
        for record in sorted(document_records, key=lambda item: item.chunk_index)
        if not is_noisy_chunk(record.text)
    ]
    if not clean_records:
        return semantic_records[:max_chunks]

    selected: dict[tuple[int, int], VectorRecord] = {}
    candidates: list[VectorRecord] = []

    for record in clean_records:
        if record.chunk_index > 25:
            continue
        _add_record(record, selected, candidates)
        if len(candidates) >= min(6, max_chunks):
            break

    diverse_target = min(max_chunks * 2, len(candidates) + 10)
    if len(candidates) < diverse_target:
        step = max(1, len(clean_records) // max(diverse_target - len(candidates), 1))
        for record in clean_records[::step]:
            _add_record(record, selected, candidates)
            if len(candidates) >= diverse_target:
                break

    for record in semantic_records:
        if record.document_id in allowed_document_ids and not is_noisy_chunk(record.text):
            _add_record(record, selected, candidates)
        if len(candidates) >= max_chunks * 3:
            break

    return rerank_chunks(question, candidates, intent)[:max_chunks]


def keyword_score(query: str, text: str) -> float:
    query_tokens = set(_tokens(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(_tokens(text))
    return len(query_tokens & text_tokens) / len(query_tokens)


def rerank_chunks(
    question: str,
    chunks: list[VectorRecord],
    intent: QueryIntent,
) -> list[VectorRecord]:
    query_embedding = embed_text(question)
    deduped: dict[tuple[int, int], VectorRecord] = {}
    seen_text: set[str] = set()
    for chunk in chunks:
        text_key = re.sub(r"\W+", " ", chunk.text.lower()).strip()[:220]
        key = (chunk.document_id, chunk.chunk_index)
        if key not in deduped and text_key not in seen_text:
            deduped[key] = chunk
            seen_text.add(text_key)

    scored = [
        (_chunk_score(question, query_embedding, chunk, intent), chunk)
        for chunk in deduped.values()
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored]


def _chunk_score(
    question: str,
    query_embedding: list[float],
    chunk: VectorRecord,
    intent: QueryIntent,
) -> float:
    score = vector_store._similarity(query_embedding, chunk.embedding)
    score += keyword_score(question, chunk.text) * 1.5
    if is_noisy_chunk(chunk.text):
        score -= 3.0

    length = len(" ".join(chunk.text.split()))
    if 250 <= length <= 1800:
        score += 0.4
    elif length < 120:
        score -= 0.8

    lower = chunk.text.lower()
    if intent in {
        QueryIntent.SUMMARY,
        QueryIntent.TOPICS,
        QueryIntent.IMPORTANT_POINTS,
        QueryIntent.STUDY_NOTES,
        QueryIntent.FLASHCARDS,
    }:
        score += sum(0.15 for term in CONCEPT_TERMS if term in lower)
        if 2 <= chunk.chunk_index <= 40:
            score += 0.25
    if intent == QueryIntent.DEFINITION and re.search(r"\b(is|refers to|defined as|means)\b", lower):
        score += 0.75
    if intent == QueryIntent.COMPARISON:
        query_tokens = _tokens(question)
        if len(set(query_tokens) & set(_tokens(chunk.text))) >= 2:
            score += 0.5
    return score


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
    if re.search(r"\.{4,}\s*\d+", normalized):
        return True

    alpha_count = sum(character.isalpha() for character in normalized)
    alpha_ratio = alpha_count / max(len(normalized), 1)
    if alpha_ratio < 0.45:
        return True

    url_count = len(re.findall(r"https?://|www\.|@\w+", lower))
    if url_count >= 2 or (url_count == 1 and len(normalized) < 220):
        return True

    symbol_count = len(re.findall(r"[{}[\]();=<>|]{1}", normalized))
    if symbol_count / max(len(normalized), 1) > 0.12:
        return True
    if re.search(r"\b(import|const|function|class|def|return|var|let)\b", lower):
        code_tokens = len(re.findall(r"\b(import|const|function|class|def|return|var|let)\b", lower))
        if code_tokens >= 3:
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


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    ]


def _add_record(
    record: VectorRecord,
    selected: dict[tuple[int, int], VectorRecord],
    merged: list[VectorRecord],
) -> None:
    key = (record.document_id, record.chunk_index)
    if key not in selected:
        merged.append(record)
        selected[key] = record
