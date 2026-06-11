from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.models.medical_claim import MedicalClaim

GRADE_SCORES: dict[str, int] = {
    "meta_analysis": 5,
    "rct": 4,
    "cohort": 3,
    "case_control": 2,
    "case_series": 1,
    "unknown": 1,
}

_LABELS: dict[int, str] = {5: "Strong", 4: "Moderate", 3: "Low", 2: "Very Low", 1: "Very Low"}


def grade_score(claim: "MedicalClaim") -> tuple[int, str]:
    base = GRADE_SCORES.get(claim.study_type, 1)
    if claim.sample_size and claim.sample_size >= 1000 and base < 5:
        base = min(base + 1, 5)
    return base, _LABELS.get(base, "Very Low")
