import re

from backend.app.services.vector_store import VectorRecord


SUMMARY_TERMS = (
    "summarize",
    "summary",
    "give me summary",
    "important topics",
    "important points",
    "key points",
    "main topics",
    "top topics",
    "explain this pdf",
    "explain this document",
    "what is this document about",
    "give me notes",
    "study notes",
    "revision notes",
    "overview",
)

COUNT_WORDS = {
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
}


def is_summary_query(query: str) -> bool:
    normalized = query.lower()
    return any(term in normalized for term in SUMMARY_TERMS) or bool(
        re.search(
            r"\b\d+\s+(?:important\b|(?:important\s+)?(?:points?|topics?|bullets?|notes?)\b)",
            normalized,
        )
    )


def extract_requested_count(query: str, default: int = 10) -> int:
    normalized = query.lower()
    patterns = (
        r"\b(\d{1,2})\s+(?:important\s+|key\s+|main\s+|top\s+)?(?:points?|topics?|bullets?|notes?)\b",
        r"\b(\d{1,2})\s+important\b",
        r"\bin\s+(\d{1,2})\s+(?:points?|topics?|bullets?|notes?)\b",
        r"\btop\s+(\d{1,2})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return _clamp_count(int(match.group(1)))

    for word, count in COUNT_WORDS.items():
        if re.search(rf"\b{word}\s+(?:important\s+|key\s+)?(?:points?|topics?|bullets?|notes?)\b", normalized):
            return _clamp_count(count)

    return _clamp_count(default)


def generate_answer(query: str, records: list[VectorRecord]) -> str:
    if not records:
        return "No relevant context found."

    if is_summary_query(query):
        return _generate_summary(query, records)
    return _generate_direct_answer(records)


def _generate_summary(query: str, records: list[VectorRecord]) -> str:
    requested_count = extract_requested_count(query)
    ordered_records = sorted(records, key=lambda record: (record.document_id, record.chunk_index))
    overview_records = ordered_records[:2]
    overview = " ".join(_sentence(record) for record in overview_records)
    important_points = _important_points(ordered_records, requested_count)
    takeaway = _sentence(ordered_records[-1])

    points = "\n".join(
        f"{index}. {point}"
        for index, point in enumerate(important_points, start=1)
    )
    return (
        f"Overview: {overview}\n\n"
        f"Important Points:\n{points}\n\n"
        f"Final Takeaway: {takeaway}"
    )


def _generate_direct_answer(records: list[VectorRecord]) -> str:
    sentences = [_sentence(record) for record in records[:3]]
    return " ".join(sentences)


def _important_points(records: list[VectorRecord], requested_count: int) -> list[str]:
    points: list[str] = []
    seen: set[str] = set()

    for record in records:
        point = _sentence(record)
        key = re.sub(r"[^a-z0-9]+", " ", point.lower()).strip()
        if key and key not in seen:
            points.append(point)
            seen.add(key)
        if len(points) == requested_count:
            return points

    fallback_record = records[-1]
    while len(points) < requested_count:
        points.append(
            "Retrieved context does not provide another distinct point. "
            f"{_citation(fallback_record)}"
        )
    return points


def _sentence(record: VectorRecord) -> str:
    text = _best_sentence(record.text)
    return f"{text} {_citation(record)}"


def _citation(record: VectorRecord) -> str:
    return f"[Document {record.document_id}, chunk {record.chunk_index}]"


def _best_sentence(text: str) -> str:
    normalized = " ".join(text.split())
    candidates = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", normalized)
        if _is_useful_sentence(sentence)
    ]
    selected = candidates[0] if candidates else normalized
    selected = re.sub(r"https?://\S+", "", selected).strip()
    if len(selected) > 260:
        selected = selected[:257].rsplit(" ", 1)[0].rstrip() + "..."
    return selected


def _is_useful_sentence(sentence: str) -> bool:
    if len(sentence) < 40:
        return False
    if re.search(r"https?://|www\.|copyright|all rights reserved|isbn", sentence, re.IGNORECASE):
        return False
    return True


def _clamp_count(count: int) -> int:
    return max(3, min(15, count))
