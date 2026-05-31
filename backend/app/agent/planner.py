from dataclasses import dataclass

from backend.app.agent.intent import (
    QueryIntent,
    detect_query_intent,
    extract_requested_count,
    extract_word_limit,
)
from backend.app.agent.skills import (
    run_comparison_skill,
    run_definition_skill,
    run_flashcard_skill,
    run_normal_qa_skill,
    run_study_notes_skill,
    run_summary_skill,
    run_topic_skill,
)
from backend.app.agent.state import ResearchAgentState


@dataclass
class AgentResult:
    answer: str
    state: ResearchAgentState


def run_research_agent(question: str, document_ids: list[int]) -> AgentResult:
    intent = detect_query_intent(question)
    state = ResearchAgentState(
        question=question,
        document_ids=document_ids,
        active_document_id=document_ids[0] if document_ids else None,
        intent=intent,
        requested_count=extract_requested_count(question),
        word_limit=extract_word_limit(question),
    )
    answer = _run_skill(state)
    return AgentResult(answer=answer, state=state)


def _run_skill(state: ResearchAgentState) -> str:
    if state.intent == QueryIntent.SUMMARY:
        return run_summary_skill(state)
    if state.intent in {QueryIntent.IMPORTANT_POINTS, QueryIntent.TOPICS}:
        return run_topic_skill(state)
    if state.intent == QueryIntent.STUDY_NOTES:
        return run_study_notes_skill(state)
    if state.intent == QueryIntent.FLASHCARDS:
        return run_flashcard_skill(state)
    if state.intent == QueryIntent.DEFINITION:
        return run_definition_skill(state)
    if state.intent == QueryIntent.COMPARISON:
        return run_comparison_skill(state)
    return run_normal_qa_skill(state)
