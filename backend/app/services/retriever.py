import re
from typing import Optional

from backend.app.agent.intent import QueryIntent
from backend.app.core.config import get_settings
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
    if is_section_lookup_query(question):
        records = retrieve_section_context(question, document_ids)
        if records:
            return records

    if is_first_mention_query(question):
        records = retrieve_first_mention_context(question, document_ids)
        if records:
            return records

    if intent in {
        QueryIntent.SUMMARY,
        QueryIntent.IMPORTANT_POINTS,
        QueryIntent.TOPICS,
        QueryIntent.STUDY_NOTES,
        QueryIntent.FLASHCARDS,
        QueryIntent.EXPLANATION,
    }:
        return retrieve_summary_context(document_ids, question, requested_count, intent)

    settings = get_settings()
    if settings.reranker_mode == "flashrank":
        top_k = max(settings.reranker_top_k, settings.reranker_final_k)
    else:
        top_k = 8 if intent == QueryIntent.COMPARISON else 5
    records = retrieve(question, top_k=top_k * 2, document_ids=document_ids)
    clean_records = [record for record in records if not is_noisy_chunk(record.text)]
    return rerank_chunks(question, clean_records or records, intent)[:top_k]


def is_section_lookup_query(question: str) -> bool:
    normalized = question.lower()
    return "section" in normalized and bool(extract_section_title(question))


def extract_section_title(question: str) -> Optional[str]:
    patterns = (
        r"\bsection\s+(?:called|titled|named)\s+['\"]([^'\"]{3,120})['\"]",
        r"\bsection\s+['\"]([^'\"]{3,120})['\"]",
        r"\bunder\s+(?:the\s+)?['\"]([^'\"]{3,120})['\"]",
    )
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def retrieve_section_context(
    question: str,
    document_ids: Optional[list[int]],
    max_records: int = 6,
) -> list[VectorRecord]:
    section_title = extract_section_title(question)
    if not section_title:
        return []

    allowed_document_ids = set(document_ids or [])
    records = [
        record
        for record in vector_store.records
        if not allowed_document_ids or record.document_id in allowed_document_ids
    ]
    records.sort(key=lambda record: (record.document_id, record.chunk_index))

    candidates: list[tuple[float, int, VectorRecord]] = []
    for position, record in enumerate(records):
        score = _section_match_score(section_title, record.text)
        if score > 0:
            candidates.append((score, position, record))

    if not candidates:
        return []

    candidates.sort(key=lambda item: (-item[0], item[2].document_id, item[2].chunk_index))
    _, start_position, matched_record = candidates[0]
    selected: list[VectorRecord] = []
    for record in records[start_position : start_position + max_records]:
        if record.document_id != matched_record.document_id:
            break
        selected.append(record)
    return selected


def is_first_mention_query(question: str) -> bool:
    normalized = question.lower()
    return (
        any(term in normalized for term in ("first time", "first mention", "first used", "very first"))
        and any(term in normalized for term in ("term", "word", "phrase"))
    )


def retrieve_first_mention_context(
    question: str,
    document_ids: Optional[list[int]],
    max_records: int = 5,
) -> list[VectorRecord]:
    terms = extract_mention_terms(question)
    if not terms:
        return []

    allowed_document_ids = set(document_ids or [])
    records = [
        record
        for record in vector_store.records
        if not allowed_document_ids or record.document_id in allowed_document_ids
    ]
    records.sort(key=lambda record: (record.document_id, record.chunk_index))

    matches = [
        record
        for record in records
        if not _is_navigation_chunk(record.text) and _record_has_sentence_match(record.text, terms)
    ]
    return matches[:max_records]


def extract_mention_terms(question: str) -> list[str]:
    quoted_terms = [
        term.strip()
        for term in re.findall(r"['\"]([^'\"]{2,80})['\"]", question)
        if term.strip()
    ]
    if quoted_terms:
        return quoted_terms

    match = re.search(r"\bterm\s+([a-z0-9][a-z0-9 -]{1,80})", question, re.IGNORECASE)
    if not match:
        return []
    raw_terms = re.split(r"\s+or\s+|\s+and\s+|,", match.group(1), flags=re.IGNORECASE)
    return [term.strip(" ?.") for term in raw_terms if term.strip(" ?.")]


def retrieve_summary_context(
    document_ids: Optional[list[int]],
    question: str,
    requested_count: int = 10,
    intent: QueryIntent = QueryIntent.SUMMARY,
) -> list[VectorRecord]:
    max_chunks = _max_broad_context_chunks(intent, requested_count)
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


def _max_broad_context_chunks(intent: QueryIntent, requested_count: int) -> int:
    if intent in {QueryIntent.SUMMARY, QueryIntent.EXPLANATION}:
        return 6
    if intent in {QueryIntent.STUDY_NOTES, QueryIntent.FLASHCARDS}:
        return min(10, max(5, requested_count + 1))
    return min(12, max(5, requested_count + 2))


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


def _record_has_sentence_match(text: str, terms: list[str]) -> bool:
    for sentence in _sentence_candidates(text):
        lower = sentence.lower()
        if any(term.lower() in lower for term in terms):
            return True
    return False


def _section_match_score(section_title: str, text: str) -> float:
    if _is_navigation_chunk(text):
        return 0.0

    normalized_title = _normalize_heading(section_title)
    normalized_text = _normalize_heading(text)
    if not normalized_title:
        return 0

    best_score = 0.0
    for line in text.splitlines():
        heading = _normalize_heading(_strip_page_marker(line))
        if not heading:
            continue
        if heading == normalized_title:
            best_score = max(best_score, 4.0)
        elif _heading_token_overlap(normalized_title, heading) >= 0.75:
            best_score = max(best_score, 3.0)

    if normalized_title in normalized_text:
        best_score = max(best_score, 2.0)
    elif _heading_token_overlap(normalized_title, normalized_text[:400]) >= 0.75:
        best_score = max(best_score, 1.0)

    return best_score


def _normalize_heading(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(normalized.split())


def _strip_page_marker(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"\.{2,}\s*\d+\s*$", "", cleaned)
    cleaned = re.sub(r"\s*\|\s*\d+\s*$", "", cleaned)
    cleaned = re.sub(r"\s{2,}\d+\s*$", "", cleaned)
    cleaned = re.sub(r"(?<=\D)\s+\d{1,4}\s*$", "", cleaned)
    cleaned = re.sub(r"^\d+\s*\|\s*", "", cleaned)
    cleaned = re.sub(r"^\d{1,4}\s+(?=\D)", "", cleaned)
    return cleaned.strip()


def _heading_token_overlap(left: str, right: str) -> float:
    ignored = {"a", "an", "are", "is", "of", "the", "why"}
    left_tokens = {token for token in left.split() if token not in ignored}
    right_tokens = {token for token in right.split() if token not in ignored}
    if not left_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens)


def _sentence_candidates(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", normalized)
        if len(sentence.strip()) >= 30 and re.search(r"[.!?]$", sentence.strip())
    ]


def _is_navigation_chunk(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    normalized = " ".join(text.split()).lower()
    if normalized.startswith(("table of contents", "contents", "index")):
        return True
    if not lines:
        return False

    navigation_lines = [
        line
        for line in lines
        if _looks_like_navigation_line(line)
    ]
    return len(navigation_lines) / len(lines) >= 0.5


def _looks_like_navigation_line(line: str) -> bool:
    normalized = line.strip().lower()
    if normalized in {"table of contents", "contents", "index"}:
        return True
    if re.search(r"\.{2,}\s*\d+\s*$", line):
        return True
    if re.search(r"\s{2,}\d+\s*$", line):
        return True
    if re.search(r"(?<=\D)\s+\d{1,4}\s*$", line) and not re.search(r"[.!?]\s*$", line):
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
