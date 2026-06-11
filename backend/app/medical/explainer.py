import logging
from typing import TYPE_CHECKING

from backend.app.medical.grader import GRADE_SCORES
from backend.app.medical.prompts import CONSENSUS_PROMPT, EXPLANATION_PROMPT
from backend.app.models.medical_claim import MedicalClaim

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from backend.app.models.contradiction import Contradiction
    from backend.app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


def explain_contradiction(
    contra: "Contradiction", db: "Session", llm: "LLMClient"
) -> str:
    claim_a = db.get(MedicalClaim, contra.claim_a_id)
    claim_b = db.get(MedicalClaim, contra.claim_b_id)
    if not claim_a or not claim_b:
        return "Unable to generate explanation: claims not found."

    prompt = EXPLANATION_PROMPT.format(
        study_type_a=claim_a.study_type,
        sample_size_a=claim_a.sample_size or "unknown",
        raw_text_a=claim_a.raw_text[:500],
        direction_a=claim_a.direction,
        study_type_b=claim_b.study_type,
        sample_size_b=claim_b.sample_size or "unknown",
        raw_text_b=claim_b.raw_text[:500],
        direction_b=claim_b.direction,
    )
    try:
        return llm.complete(prompt).strip()
    except Exception as exc:
        logger.error("Explanation generation failed: %s", exc)
        return "Explanation unavailable due to LLM error."


def generate_consensus(
    drug: str, condition: str, claims: list[MedicalClaim], llm: "LLMClient"
) -> str:
    sorted_claims = sorted(
        claims,
        key=lambda c: GRADE_SCORES.get(c.study_type, 1),
        reverse=True,
    )

    lines = []
    for c in sorted_claims[:10]:
        lines.append(
            f"- [{c.study_type}, n={c.sample_size or '?'}] "
            f"{c.direction}: {c.raw_text[:200]}"
        )
    claims_text = "\n".join(lines)

    prompt = CONSENSUS_PROMPT.format(
        drug=drug,
        condition=condition,
        claims_text=claims_text,
    )
    try:
        return llm.complete(prompt).strip()
    except Exception as exc:
        logger.error("Consensus generation failed: %s", exc)
        return "Consensus unavailable due to LLM error."
