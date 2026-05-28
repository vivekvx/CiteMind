import json
import re
import urllib.request
from typing import Optional, Tuple

from backend.app.agent.intent import (
    QueryIntent,
    detect_query_intent,
    extract_requested_count,
)
from backend.app.core.config import get_settings
from backend.app.services.vector_store import VectorRecord


BROAD_INTENTS = {
    QueryIntent.SUMMARY,
    QueryIntent.IMPORTANT_POINTS,
    QueryIntent.TOPICS,
    QueryIntent.STUDY_NOTES,
    QueryIntent.FLASHCARDS,
    QueryIntent.EXPLANATION,
}


def is_summary_or_topic_query(query: str) -> bool:
    return detect_query_intent(query) in BROAD_INTENTS


def is_summary_query(query: str) -> bool:
    return is_summary_or_topic_query(query)


def generate_answer(
    query: str,
    records: list[VectorRecord],
    intent: Optional[QueryIntent] = None,
    requested_count: Optional[int] = None,
) -> str:
    answer, _ = generate_answer_result(query, records, intent, requested_count)
    return answer


def generate_answer_result(
    query: str,
    records: list[VectorRecord],
    intent: Optional[QueryIntent] = None,
    requested_count: Optional[int] = None,
) -> Tuple[str, bool]:
    if not records:
        return "No relevant context found.", False

    intent = intent or detect_query_intent(query)
    requested_count = requested_count or extract_requested_count(query)
    llm_answer = _generate_llm_answer(query, records, intent, requested_count)
    if llm_answer:
        return llm_answer, True

    fallback_prefix = (
        "LLM generation is not configured. Add OPENAI_API_KEY to .env to enable "
        "synthesized answers. Here is a limited extractive fallback:\n\n"
        if not get_settings().openai_api_key
        else "LLM generation failed. Here is a limited extractive fallback:\n\n"
    )

    if intent == QueryIntent.SUMMARY:
        return fallback_prefix + _generate_summary(records), False
    if intent in {QueryIntent.IMPORTANT_POINTS, QueryIntent.TOPICS}:
        return fallback_prefix + _generate_topics(records, requested_count), False
    if intent == QueryIntent.STUDY_NOTES:
        return fallback_prefix + _generate_study_notes(records, requested_count), False
    if intent == QueryIntent.FLASHCARDS:
        return fallback_prefix + _generate_flashcards(records, requested_count), False
    if intent == QueryIntent.COMPARISON:
        return fallback_prefix + _generate_comparison(query, records), False
    if intent == QueryIntent.DEFINITION:
        return fallback_prefix + _generate_definition(records), False
    if intent == QueryIntent.EXPLANATION:
        return fallback_prefix + _generate_explanation(records), False
    return fallback_prefix + _generate_direct_answer(records), False


def _generate_llm_answer(
    query: str,
    records: list[VectorRecord],
    intent: QueryIntent,
    requested_count: int,
) -> Optional[str]:
    settings = get_settings()
    if not settings.openai_api_key:
        return None

    payload = {
        "model": settings.openai_chat_model,
        "messages": [
            {
                "role": "system",
                "content": _system_prompt(intent, requested_count),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {query}\n\n"
                    f"Requested count: {requested_count}\n\n"
                    f"Retrieved context:\n{_format_context(records)}"
                ),
            },
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def _system_prompt(intent: QueryIntent, requested_count: int) -> str:
    base = (
        "You are CiteMind, a document-aware research assistant. Use only the "
        "retrieved context. Synthesize rather than copying chunks. Ignore noisy "
        "front matter, praise, copyright, acknowledgements, publisher info, links, "
        "code-only snippets, and boilerplate. Every factual claim that depends on "
        "context needs an inline citation exactly like [Document X, chunk Y]. If "
        "context is insufficient, say what is missing and do not fabricate.\n\n"
    )
    if intent == QueryIntent.STUDY_NOTES:
        return base + (
            "Output exactly this format:\n"
            "Study Notes:\n"
            "1. <Concept name>\n"
            "   - Explanation: <clear, specific explanation>\n"
            "   - Why it matters: <specific importance from context>\n"
            "   - Citation: [Document X, chunk Y]\n"
            f"Create up to {requested_count} useful notes."
        )
    if intent in {QueryIntent.TOPICS, QueryIntent.IMPORTANT_POINTS}:
        return base + (
            "Output exactly this format:\n"
            "Overview:\n<2-3 concise sentences>\n\n"
            f"{requested_count} Important Topics:\n"
            "1. <Topic name>: <short explanation> [Document X, chunk Y]\n"
            f"...\n{requested_count}. <Topic name>: <short explanation> [Document X, chunk Y]\n\n"
            "Final Takeaway:\n<1-2 sentences>\n"
            f"Output exactly {requested_count} numbered topics."
        )
    if intent == QueryIntent.SUMMARY:
        return base + (
            "Output exactly this format:\n"
            "Overview:\n<clear summary>\n\n"
            "Key Ideas:\n- <idea> [Document X, chunk Y]\n- <idea> [Document X, chunk Y]\n\n"
            "Final Takeaway:\n<1-2 sentences>"
        )
    if intent == QueryIntent.FLASHCARDS:
        return base + (
            "Output exactly this format:\n"
            "Flashcards:\n"
            "1. Q: <question>\n"
            "   A: <answer> [Document X, chunk Y]\n"
            f"Create up to {requested_count} flashcards."
        )
    if intent == QueryIntent.DEFINITION:
        return base + "Start with `Definition:` and answer concisely with citations."
    if intent == QueryIntent.COMPARISON:
        return base + "Output a concise markdown comparison table with citations in cells."
    return base + "Output `Answer:` followed by a concise direct answer with citations."


def _format_context(records: list[VectorRecord]) -> str:
    return "\n\n".join(
        f"[Document {record.document_id}, chunk {record.chunk_index}]\n{record.text}"
        for record in records
    )


def _generate_summary(records: list[VectorRecord]) -> str:
    ordered_records = sorted(records, key=lambda record: (record.document_id, record.chunk_index))
    overview_records = ordered_records[:2]
    overview = " ".join(_sentence(record) for record in overview_records)
    sections = "\n".join(
        f"* {_topic_name(_best_sentence(record.text))} {_citation(record)}"
        for record in ordered_records[2:8]
    )
    if not sections:
        sections = f"* Main document theme {_citation(ordered_records[0])}"
    takeaway = _sentence(ordered_records[-1])
    return (
        f"Overview:\n{overview}\n\n"
        f"Key Sections:\n{sections}\n\n"
        f"Final Takeaway:\n{takeaway}"
    )


def _generate_topics(records: list[VectorRecord], requested_count: int) -> str:
    ordered_records = sorted(records, key=lambda record: (record.document_id, record.chunk_index))
    overview_records = ordered_records[:2]
    overview = " ".join(_sentence(record) for record in overview_records)
    important_points = _important_topics(ordered_records, requested_count)
    takeaway = _sentence(ordered_records[-1])
    points = "\n".join(
        f"{index}. {point}"
        for index, point in enumerate(important_points, start=1)
    )
    return (
        f"Overview: {overview}\n\n"
        f"{requested_count} Important Topics:\n{points}\n\n"
        f"Final Takeaway: {takeaway}"
    )


def _generate_direct_answer(records: list[VectorRecord]) -> str:
    sentences = [_sentence(record) for record in records[:3]]
    return f"Answer: {' '.join(sentences)}"


def _generate_definition(records: list[VectorRecord]) -> str:
    return f"Definition: {_sentence(records[0])}"


def _generate_explanation(records: list[VectorRecord]) -> str:
    sentences = [_sentence(record) for record in records[:5]]
    return "Explanation:\n" + "\n".join(f"- {sentence}" for sentence in sentences)


def _generate_study_notes(records: list[VectorRecord], requested_count: int) -> str:
    ordered_records = sorted(records, key=lambda record: (record.document_id, record.chunk_index))
    notes = []
    for index, record in enumerate(ordered_records[:requested_count], start=1):
        explanation = _best_sentence(record.text)
        notes.append(
            f"{index}. {_topic_name(explanation)}\n"
            f"   * Explanation: {explanation}\n"
            f"   * Why it matters: The document connects this point to {_topic_name(explanation).lower()} in the cited section. {_citation(record)}"
        )
    return "Study Notes:\n\n" + "\n\n".join(notes)


def _generate_flashcards(records: list[VectorRecord], requested_count: int) -> str:
    ordered_records = sorted(records, key=lambda record: (record.document_id, record.chunk_index))
    cards = []
    for index, record in enumerate(ordered_records[:requested_count], start=1):
        explanation = _best_sentence(record.text)
        cards.append(
            f"{index}. Q: What should you know about {_topic_name(explanation)}?\n"
            f"   A: {explanation} {_citation(record)}"
        )
    return "Flashcards:\n\n" + "\n\n".join(cards)


def _generate_comparison(query: str, records: list[VectorRecord]) -> str:
    left, right = _comparison_terms(query)
    left_record = records[0]
    right_record = records[1] if len(records) > 1 else records[0]
    return (
        "Comparison:\n\n"
        "| Aspect | Concept A | Concept B |\n"
        "| ------ | --------- | --------- |\n"
        f"| Focus | {left}: {_best_sentence(left_record.text)} {_citation(left_record)} | "
        f"{right}: {_best_sentence(right_record.text)} {_citation(right_record)} |"
    )


def _important_topics(records: list[VectorRecord], requested_count: int) -> list[str]:
    points: list[str] = []
    seen: set[str] = set()

    for record in records:
        point = _topic_point(record)
        key = re.sub(r"[^a-z0-9]+", " ", point.split(":", 1)[0].lower()).strip()
        if key and key not in seen:
            points.append(point)
            seen.add(key)
        if len(points) == requested_count:
            return points

    fallback_record = records[-1]
    while len(points) < requested_count:
        points.append(
            "Insufficient high-quality context: Retrieved context does not provide another distinct topic. "
            f"{_citation(fallback_record)}"
        )
    return points


def _topic_point(record: VectorRecord) -> str:
    explanation = _best_sentence(record.text)
    topic = _topic_name(explanation)
    return f"{topic}: {explanation} {_citation(record)}"


def _sentence(record: VectorRecord) -> str:
    text = _best_sentence(record.text)
    return f"{text} {_citation(record)}"


def _citation(record: VectorRecord) -> str:
    return f"[Document {record.document_id}, chunk {record.chunk_index}]"


def _best_sentence(text: str) -> str:
    normalized = " ".join(text.split())
    normalized = re.sub(r"```.*?```", "", normalized)
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


def _topic_name(sentence: str) -> str:
    cleaned = re.sub(r"\[[^\]]+\]", "", sentence).strip()
    match = re.match(
        r"(.{3,80}?)\s+(?:is|are|uses|helps|enables|allows|provides|supports|explains|describes|introduces|covers|connects|builds)\b",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        candidate = match.group(1)
    else:
        candidate = " ".join(cleaned.split()[:6])
    candidate = re.sub(r"^(this|the|a|an)\s+", "", candidate, flags=re.IGNORECASE)
    candidate = candidate.strip(" :-,.;")
    if len(candidate) > 56:
        candidate = candidate[:53].rsplit(" ", 1)[0].rstrip() + "..."
    return candidate[:1].upper() + candidate[1:] if candidate else "Important topic"


def _comparison_terms(query: str) -> Tuple[str, str]:
    match = re.search(r"compare\s+(.+?)\s+(?:and|with|vs\.?|versus)\s+(.+)", query, re.IGNORECASE)
    if not match:
        match = re.search(r"difference between\s+(.+?)\s+and\s+(.+)", query, re.IGNORECASE)
    if match:
        return match.group(1).strip(" ?."), match.group(2).strip(" ?.")
    return "Concept A", "Concept B"


def _is_useful_sentence(sentence: str) -> bool:
    if len(sentence) < 40:
        return False
    if re.search(
        r"https?://|www\.|copyright|all rights reserved|isbn|praise for|acknowledgements|acknowledgments|disclaimer|liability",
        sentence,
        re.IGNORECASE,
    ):
        return False
    return True
