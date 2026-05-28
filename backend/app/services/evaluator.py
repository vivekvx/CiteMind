from __future__ import annotations

import json
import os
import re
import urllib.request

from backend.app.schemas.eval import EvalRunRequest
from backend.app.agent.intent import (
    detect_query_intent,
    extract_requested_count,
    QueryIntent,
)


def evaluate(request: EvalRunRequest) -> dict[str, float]:
    if os.getenv("OPENAI_API_KEY"):
        scores = _llm_scores(request)
        if scores:
            return scores
    return _heuristic_scores(request)


def _llm_scores(request: EvalRunRequest) -> dict[str, float] | None:
    prompt = (
        "Score this RAG answer from 0 to 1 as JSON with keys "
        "faithfulness_score, answer_relevance_score, context_relevance_score, "
        "citation_coverage_score.\n"
        f"Query: {request.query}\n"
        f"Answer: {request.answer}\n"
        f"Contexts: {request.contexts}\n"
        f"Citations: {request.citations}\n"
    )
    payload = {
        "model": os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    http_request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(_extract_json(content))
        return _clamp_scores(parsed)
    except Exception:
        return None


def _heuristic_scores(request: EvalRunRequest) -> dict[str, float]:
    answer_tokens = _tokens(request.answer)
    query_tokens = _tokens(request.query)
    context_tokens = _tokens(" ".join(request.contexts))

    faithfulness = _overlap(answer_tokens, context_tokens) if context_tokens else 0.0
    answer_relevance = max(
        _overlap(query_tokens, answer_tokens),
        _structured_answer_relevance(request.query, request.answer),
    )
    context_relevance = _overlap(query_tokens, context_tokens) if context_tokens else 0.0
    if detect_query_intent(request.query) in {
        QueryIntent.SUMMARY,
        QueryIntent.IMPORTANT_POINTS,
        QueryIntent.TOPICS,
        QueryIntent.STUDY_NOTES,
    }:
        context_relevance = max(context_relevance, _overlap(answer_tokens, context_tokens))
    citation_coverage = _citation_coverage(request.answer, len(request.citations))

    return _clamp_scores(
        {
            "faithfulness_score": faithfulness,
            "answer_relevance_score": answer_relevance,
            "context_relevance_score": context_relevance,
            "citation_coverage_score": citation_coverage,
        }
    )


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _overlap(left: set[str], right: set[str]) -> float:
    if not left:
        return 0.0
    return len(left & right) / len(left)


def _citation_coverage(answer: str, citation_count: int) -> float:
    bracket_count = len(re.findall(r"\[Document\s+\d+,\s+chunk\s+\d+\]", answer))
    numbered_lines = re.findall(r"^\d+\.\s+.+$", answer, re.MULTILINE)
    if numbered_lines:
        cited_numbered_lines = [
            line
            for line in numbered_lines
            if re.search(r"\[Document\s+\d+,\s+chunk\s+\d+\]", line)
        ]
        return len(cited_numbered_lines) / len(numbered_lines)
    if citation_count == 0:
        return 0.0
    return min(1.0, bracket_count / citation_count)


def _structured_answer_relevance(query: str, answer: str) -> float:
    intent = detect_query_intent(query)
    if intent in {QueryIntent.IMPORTANT_POINTS, QueryIntent.TOPICS}:
        requested_count = extract_requested_count(query)
        numbered_count = len(re.findall(r"^\d+\.\s+", answer, re.MULTILINE))
        has_overview = "Overview:" in answer
        has_takeaway = "Final Takeaway:" in answer
        if numbered_count == requested_count and has_overview and has_takeaway:
            return 0.9
    if intent == QueryIntent.SUMMARY and "Overview:" in answer and "Final Takeaway:" in answer:
        return 0.8
    if intent == QueryIntent.STUDY_NOTES and "Study Notes:" in answer:
        return 0.8
    return 0.0


def _extract_json(content: str) -> str:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    return match.group(0) if match else content


def _clamp_scores(scores: dict[str, float]) -> dict[str, float]:
    keys = [
        "faithfulness_score",
        "answer_relevance_score",
        "context_relevance_score",
        "citation_coverage_score",
    ]
    return {key: max(0.0, min(1.0, float(scores.get(key, 0.0)))) for key in keys}
