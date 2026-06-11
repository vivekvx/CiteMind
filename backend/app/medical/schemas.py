from typing import Optional

from pydantic import BaseModel


class ClaimOut(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    drug: str
    condition: str
    outcome: str
    direction: str
    population: Optional[str]
    study_type: str
    sample_size: Optional[int]
    effect_size: Optional[str]
    confidence: float
    raw_text: str
    grade_score: int
    evidence_label: str

    model_config = {"from_attributes": True}


class ContradictionOut(BaseModel):
    id: int
    claim_a: ClaimOut
    claim_b: ClaimOut
    contradiction_type: str
    severity: str
    explanation: Optional[str]
    consensus: Optional[str]


class AnalysisReport(BaseModel):
    job_id: str
    document_ids: list[int]
    total_claims: int
    total_contradictions: int
    contradictions: list[ContradictionOut]
