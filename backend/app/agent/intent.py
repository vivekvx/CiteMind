import re
from enum import Enum
from typing import Optional


class QueryIntent(str, Enum):
    SUMMARY = "summary"
    IMPORTANT_POINTS = "important_points"
    TOPICS = "topics"
    STUDY_NOTES = "study_notes"
    FLASHCARDS = "flashcards"
    EXPLANATION = "explanation"
    DEFINITION = "definition"
    COMPARISON = "comparison"
    NORMAL_QA = "normal_qa"


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
    "twenty": 20,
}


def detect_query_intent(question: str) -> QueryIntent:
    normalized = question.lower()
    if "flashcard" in normalized:
        return QueryIntent.FLASHCARDS
    if (
        "compare" in normalized
        or "difference between" in normalized
        or "versus" in normalized
        or " vs " in normalized
    ):
        return QueryIntent.COMPARISON
    if any(term in normalized for term in ("give me notes", "make notes", "study notes", "revision notes")):
        return QueryIntent.STUDY_NOTES
    if any(term in normalized for term in ("important points", "key points")):
        return QueryIntent.IMPORTANT_POINTS
    if any(term in normalized for term in ("important topics", "key topics", "main topics", "top topics")):
        return QueryIntent.TOPICS
    if re.search(r"\b\d+\s+(?:important\b|(?:important\s+)?(?:points?|topics?|bullets?|notes?)\b)", normalized):
        return QueryIntent.TOPICS
    if any(term in normalized for term in ("summarize", "summary", "overview", "what is this document about")):
        return QueryIntent.SUMMARY
    if "explain this pdf" in normalized or "explain this document" in normalized or normalized.startswith("explain "):
        return QueryIntent.EXPLANATION
    if normalized.startswith(("define ", "what is ", "what are ", "meaning of ")):
        return QueryIntent.DEFINITION
    return QueryIntent.NORMAL_QA


def extract_requested_count(question: str, default: int = 10) -> int:
    normalized = question.lower()
    patterns = (
        r"\bexactly\s+(\d{1,2})\s+(?:important\s+|key\s+|main\s+|top\s+)?(?:points?|topics?|bullets?|notes?)\b",
        r"\bmake\s+(\d{1,2})\s+flashcards?\b",
        r"\b(\d{1,2})\s+(?:important\s+|key\s+|main\s+|top\s+)?(?:points?|topics?|bullets?|notes?)\b",
        r"\b(\d{1,2})\s+flashcards?\b",
        r"\b(\d{1,2})\s+important\b",
        r"\bin\s+(\d{1,2})\s+(?:points?|topics?|bullets?|notes?)\b",
        r"\btop\s+(\d{1,2})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return _clamp_count(int(match.group(1)))

    for word, count in COUNT_WORDS.items():
        if re.search(rf"\b{word}\s+(?:important\s+|key\s+)?(?:points?|topics?|bullets?|notes?|flashcards?)\b", normalized):
            return _clamp_count(count)

    return _clamp_count(default)


def extract_word_limit(question: str) -> Optional[int]:
    normalized = question.lower()
    patterns = (
        r"\b(?:in|under|within|around|about|approximately|approx\.?)\s+(\d{1,4})\s+words?\b",
        r"\b(\d{1,4})\s+words?\b",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return _clamp_word_limit(int(match.group(1)))
    return None


def _clamp_count(count: int) -> int:
    return max(3, min(20, count))


def _clamp_word_limit(count: int) -> int:
    return max(30, min(1000, count))
