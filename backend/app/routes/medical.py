import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.medical.detector import detect_contradictions
from backend.app.medical.explainer import explain_contradiction, generate_consensus
from backend.app.medical.extractor import extract_claims
from backend.app.medical.grader import grade_score
from backend.app.medical.schemas import AnalysisReport, ClaimOut, ContradictionOut
from backend.app.models.analysis_job import AnalysisJob
from backend.app.models.contradiction import Contradiction
from backend.app.models.medical_claim import MedicalClaim
from backend.app.services.llm_client import LLMClient


class AnalyzeRequest(BaseModel):
    document_ids: list[int]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/medical", tags=["medical"])
_llm = LLMClient()


def _to_out(claim: MedicalClaim) -> ClaimOut:
    score, label = grade_score(claim)
    return ClaimOut(
        id=claim.id,
        document_id=claim.document_id,
        chunk_index=claim.chunk_index,
        drug=claim.drug,
        condition=claim.condition,
        outcome=claim.outcome,
        direction=claim.direction,
        population=claim.population,
        study_type=claim.study_type,
        sample_size=claim.sample_size,
        effect_size=claim.effect_size,
        confidence=claim.confidence,
        raw_text=claim.raw_text,
        grade_score=score,
        evidence_label=label,
    )


@router.post("/extract/{document_id}")
def trigger_extraction(document_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        claims = extract_claims(document_id, db, _llm)
    except Exception as exc:
        logger.error("Extraction error doc %d: %s", document_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))
    return {"document_id": document_id, "count": len(claims)}


@router.get("/claims/{document_id}", response_model=list[ClaimOut])
def get_claims(document_id: int, db: Session = Depends(get_db)) -> list[ClaimOut]:
    claims = db.scalars(
        select(MedicalClaim)
        .where(MedicalClaim.document_id == document_id)
        .order_by(MedicalClaim.id)
    ).all()
    return [_to_out(c) for c in claims]


# Vercel serverless functions have a hard timeout (10s hobby / 60s pro).
# Each explanation is an LLM call, so only the most severe contradictions
# get inline explanations; the rest stay on-demand via POST /medical/explain/{id}.
_MAX_INLINE_EXPLANATIONS = 5
_SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


@router.post("/analyze", response_model=AnalysisReport)
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalysisReport:
    doc_ids = body.document_ids
    if len(doc_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 document_ids required.")

    job_id = str(uuid.uuid4())
    job = AnalysisJob(id=job_id, document_ids_json=json.dumps(doc_ids), status="running")
    db.add(job)
    db.commit()

    try:
        report = _run_analysis(job_id, doc_ids, db)
    except Exception as exc:
        logger.error("Analysis failed job %s: %s", job_id, exc)
        job.status = "failed"
        job.error = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc))

    job.status = "done"
    job.result_json = report.model_dump_json()
    job.completed_at = datetime.utcnow()
    db.commit()
    return report


def _run_analysis(job_id: str, doc_ids: list[int], db: Session) -> AnalysisReport:
    contradictions = detect_contradictions(doc_ids, db)
    all_claims = list(
        db.scalars(
            select(MedicalClaim).where(MedicalClaim.document_id.in_(doc_ids))
        ).all()
    )
    claim_map = {c.id: _to_out(c) for c in all_claims}
    claims_by_id = {c.id: c for c in all_claims}

    by_severity = sorted(
        contradictions,
        key=lambda c: _SEVERITY_ORDER.get(c.severity, len(_SEVERITY_ORDER)),
    )
    for c in by_severity[:_MAX_INLINE_EXPLANATIONS]:
        c.explanation = explain_contradiction(c, db, _llm)

    _generate_consensus_for_contradictions(contradictions, all_claims, claims_by_id)

    contra_out = [_contra_to_out(c, claim_map, claims_by_id) for c in contradictions]

    return AnalysisReport(
        job_id=job_id,
        document_ids=doc_ids,
        total_claims=len(all_claims),
        total_contradictions=len(contradictions),
        contradictions=contra_out,
    )


@router.get("/analyze/{job_id}", response_model=AnalysisReport)
def get_analysis(job_id: str, db: Session = Depends(get_db)) -> AnalysisReport:
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status == "failed":
        raise HTTPException(status_code=500, detail=job.error or "Analysis failed.")
    if job.status != "done" or not job.result_json:
        raise HTTPException(status_code=202, detail="Analysis still running.")
    return AnalysisReport.model_validate_json(job.result_json)


@router.post("/explain/{contradiction_id}")
def explain(contradiction_id: int, db: Session = Depends(get_db)) -> dict:
    contra = db.get(Contradiction, contradiction_id)
    if not contra:
        raise HTTPException(status_code=404, detail="Contradiction not found.")
    explanation = explain_contradiction(contra, db, _llm)
    contra.explanation = explanation
    db.commit()
    return {"contradiction_id": contradiction_id, "explanation": explanation}


def _generate_consensus_for_contradictions(
    contradictions: list[Contradiction],
    all_claims: list[MedicalClaim],
    claims_by_id: dict[int, MedicalClaim],
) -> None:
    groups: dict[tuple[str, str], list[int]] = {}
    for c in contradictions:
        claim_a = claims_by_id.get(c.claim_a_id)
        claim_b = claims_by_id.get(c.claim_b_id)
        if claim_a and claim_b:
            key = (claim_a.drug.lower().strip(), claim_a.condition.lower().strip())
            groups.setdefault(key, []).append(c.id)

    claim_by_key: dict[tuple[str, str], list[MedicalClaim]] = {}
    for claim in all_claims:
        key = (claim.drug.lower().strip(), claim.condition.lower().strip())
        claim_by_key.setdefault(key, []).append(claim)

    contra_map = {c.id: c for c in contradictions}
    for key, contra_ids in groups.items():
        drug, condition = key
        claims_for_group = claim_by_key.get(key, [])
        if not claims_for_group:
            continue
        consensus = generate_consensus(drug, condition, claims_for_group, _llm)
        for cid in contra_ids:
            if cid in contra_map:
                contra_map[cid].consensus = consensus


def _contra_to_out(
    c: Contradiction,
    claim_map: dict[int, ClaimOut],
    claims_by_id: dict[int, MedicalClaim],
) -> ContradictionOut:
    claim_a = claim_map.get(c.claim_a_id)
    claim_b = claim_map.get(c.claim_b_id)
    if not claim_a:
        raw = claims_by_id.get(c.claim_a_id)
        claim_a = _to_out(raw) if raw else None
    if not claim_b:
        raw = claims_by_id.get(c.claim_b_id)
        claim_b = _to_out(raw) if raw else None
    return ContradictionOut(
        id=c.id,
        claim_a=claim_a,
        claim_b=claim_b,
        contradiction_type=c.contradiction_type,
        severity=c.severity,
        explanation=c.explanation,
        consensus=c.consensus,
    )
