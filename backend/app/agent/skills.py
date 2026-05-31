from backend.app.agent.intent import QueryIntent
from backend.app.agent.state import ResearchAgentState
from backend.app.services.answer_generator import generate_answer_result
from backend.app.services.retriever import retrieve_context_for_intent


def run_summary_skill(state: ResearchAgentState) -> str:
    return _run_with_intent(state, QueryIntent.SUMMARY)


def run_topic_skill(state: ResearchAgentState) -> str:
    return _run_with_intent(state, state.intent)


def run_study_notes_skill(state: ResearchAgentState) -> str:
    return _run_with_intent(state, QueryIntent.STUDY_NOTES)


def run_flashcard_skill(state: ResearchAgentState) -> str:
    return _run_with_intent(state, QueryIntent.FLASHCARDS)


def run_normal_qa_skill(state: ResearchAgentState) -> str:
    return _run_with_intent(state, QueryIntent.NORMAL_QA)


def run_definition_skill(state: ResearchAgentState) -> str:
    return _run_with_intent(state, QueryIntent.DEFINITION)


def run_comparison_skill(state: ResearchAgentState) -> str:
    return _run_with_intent(state, QueryIntent.COMPARISON)


def _run_with_intent(state: ResearchAgentState, intent: QueryIntent) -> str:
    state.intent = intent
    state.retrieved_chunks = retrieve_context_for_intent(
        question=state.question,
        document_ids=state.document_ids,
        intent=state.intent,
        requested_count=state.requested_count,
    )
    answer, used_llm = generate_answer_result(
        state.question,
        state.retrieved_chunks,
        state.intent,
        state.requested_count,
        state.word_limit,
    )
    state.used_llm = used_llm
    return answer
