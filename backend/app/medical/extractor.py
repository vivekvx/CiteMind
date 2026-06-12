import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.medical.prompts import EXTRACTION_PROMPT
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.medical_claim import MedicalClaim
from backend.app.services.llm_client import LLMClient, parse_json_response

logger = logging.getLogger(__name__)

_MEDICAL_KEYWORDS = {
    "mg", "drug", "dose", "patient", "trial", "study", "treatment", "therapy",
    "clinical", "placebo", "efficacy", "safety", "adverse", "mortality",
    "survival", "outcome", "diabetes", "cancer", "hypertension", "infection",
    "randomized", "cohort", "meta-analysis", "systematic review", "rct",
    "chemotherapy", "antibiotic", "vaccine", "cardiovascular", "renal",
}


def _looks_medical(text: str) -> bool:
    lower = text.lower()
    return sum(1 for kw in _MEDICAL_KEYWORDS if kw in lower) >= 2


def extract_claims(document_id: int, db: Session, llm: LLMClient) -> list[MedicalClaim]:
    # Idempotent: delete existing claims first
    db.execute(delete(MedicalClaim).where(MedicalClaim.document_id == document_id))
    db.commit()

    chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    ).all()

    saved: list[MedicalClaim] = []
    for chunk in chunks:
        if not _looks_medical(chunk.text):
            continue
        try:
            prompt = EXTRACTION_PROMPT.format(chunk_text=chunk.text[:3000])
            raw_response = llm.complete(prompt, json_mode=True)
            data = parse_json_response(raw_response)
            raw_claims = data.get("claims", [])
            if not isinstance(raw_claims, list):
                continue
        except Exception as exc:
            logger.warning("Extraction failed chunk %d doc %d: %s", chunk.chunk_index, document_id, exc)
            continue

        for raw in raw_claims:
            if not isinstance(raw, dict):
                continue
            try:
                conf = float(raw.get("confidence", 0))
            except (TypeError, ValueError):
                conf = 0.0
            if conf < 0.4:
                continue
            drug = str(raw.get("drug") or "").strip()[:255]
            condition = str(raw.get("condition") or "").strip()[:255]
            outcome = str(raw.get("outcome") or "").strip()[:255]
            if not drug or not condition or not outcome:
                continue
            direction = str(raw.get("direction") or "unclear").lower().strip()
            if direction not in ("positive", "negative", "neutral", "unclear"):
                direction = "unclear"
            study_type = str(raw.get("study_type") or "unknown").lower().strip()
            if study_type not in ("meta_analysis", "rct", "cohort", "case_control", "case_series"):
                study_type = "unknown"
            try:
                sample_size = int(raw["sample_size"]) if raw.get("sample_size") else None
            except (TypeError, ValueError):
                sample_size = None
            claim = MedicalClaim(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                drug=drug,
                condition=condition,
                outcome=outcome,
                direction=direction,
                population=str(raw.get("population") or "")[:500] or None,
                study_type=study_type,
                sample_size=sample_size,
                effect_size=str(raw.get("effect_size") or "")[:255] or None,
                confidence=float(raw.get("confidence", 0.5)),
                raw_text=str(raw.get("raw_text") or chunk.text[:500]),
            )
            db.add(claim)
            saved.append(claim)

    db.commit()
    for c in saved:
        db.refresh(c)
    return saved
