import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.contradiction import Contradiction
from backend.app.models.medical_claim import MedicalClaim

logger = logging.getLogger(__name__)

_HIGH_EVIDENCE = {"meta_analysis", "rct"}
_LOW_EVIDENCE = {"case_series", "unknown"}


def detect_contradictions(document_ids: list[int], db: Session) -> list[Contradiction]:
    claims = list(
        db.scalars(
            select(MedicalClaim).where(MedicalClaim.document_id.in_(document_ids))
        ).all()
    )

    groups: dict[tuple[str, str, str], list[MedicalClaim]] = defaultdict(list)
    for claim in claims:
        key = (
            claim.drug.lower().strip(),
            claim.condition.lower().strip(),
            claim.outcome.lower().strip(),
        )
        groups[key].append(claim)

    saved: list[Contradiction] = []
    for group in groups.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a.document_id == b.document_id:
                    continue
                if a.direction not in ("positive", "negative"):
                    continue
                if b.direction not in ("positive", "negative"):
                    continue
                if a.direction == b.direction:
                    continue
                saved.append(
                    Contradiction(
                        claim_a_id=a.id,
                        claim_b_id=b.id,
                        contradiction_type=_classify_type(a, b),
                        severity=_assess_severity(a, b),
                    )
                )

    if saved:
        db.add_all(saved)
        db.commit()
        for c in saved:
            db.refresh(c)

    return saved


def _classify_type(a: MedicalClaim, b: MedicalClaim) -> str:
    if a.study_type != b.study_type and {a.study_type, b.study_type} & _HIGH_EVIDENCE:
        return "METHODOLOGICAL"
    return "DIRECT"


def _assess_severity(a: MedicalClaim, b: MedicalClaim) -> str:
    types = {a.study_type, b.study_type}
    if types & _HIGH_EVIDENCE:
        return "HIGH"
    if types <= _LOW_EVIDENCE:
        return "LOW"
    return "MEDIUM"
