"""End-to-end pipeline test: seed docs -> extract (mock LLM) -> detect -> grade."""

import json
import os
import tempfile

_TEMP_DIR = tempfile.TemporaryDirectory()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEMP_DIR.name}/test-pipeline.db")

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.medical.detector import detect_contradictions
from backend.app.medical.extractor import extract_claims
from backend.app.medical.grader import grade_score
from backend.app.models.base import Base
from backend.app.models.contradiction import Contradiction
from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.medical_claim import MedicalClaim

engine = create_engine(f"sqlite:///{_TEMP_DIR.name}/test-pipeline.db")
Base.metadata.create_all(engine)

RCT_TEXT = (
    "In this randomized controlled trial of 4200 patients, atorvastatin "
    "treatment significantly reduced cardiovascular mortality compared to placebo."
)
COHORT_TEXT = (
    "In this retrospective cohort study of 890 elderly patients, atorvastatin "
    "therapy showed negative outcomes for cardiovascular mortality."
)

RCT_CLAIM = {
    "claims": [
        {
            "drug": "atorvastatin",
            "condition": "hypercholesterolemia",
            "outcome": "cardiovascular mortality",
            "direction": "positive",
            "population": "adults 45-75",
            "study_type": "rct",
            "sample_size": 4200,
            "effect_size": "HR 0.72",
            "confidence": 0.95,
        }
    ]
}
COHORT_CLAIM = {
    "claims": [
        {
            "drug": "atorvastatin",
            "condition": "hypercholesterolemia",
            "outcome": "cardiovascular mortality",
            "direction": "negative",
            "population": "elderly >75",
            "study_type": "cohort",
            "sample_size": 890,
            "effect_size": "HR 1.12",
            "confidence": 0.85,
        }
    ]
}


class MockLLM:
    """Returns a canned claim payload depending on which chunk is being read."""

    def complete(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        if "randomized controlled trial" in prompt:
            return json.dumps(RCT_CLAIM)
        if "retrospective cohort" in prompt:
            return json.dumps(COHORT_CLAIM)
        return json.dumps({"claims": []})


class TestPipelineIntegration(unittest.TestCase):
    def setUp(self):
        with Session(engine) as db:
            db.query(Contradiction).delete()
            db.query(MedicalClaim).delete()
            db.query(DocumentChunk).delete()
            db.query(Document).delete()
            db.commit()

    def _seed(self, db: Session) -> "tuple[int, int]":
        doc_a = Document(title="statin_rct.md", content_hash="ha")
        doc_b = Document(title="statin_cohort.md", content_hash="hb")
        db.add_all([doc_a, doc_b])
        db.commit()
        db.add_all(
            [
                DocumentChunk(document_id=doc_a.id, chunk_index=0, text=RCT_TEXT),
                DocumentChunk(document_id=doc_b.id, chunk_index=0, text=COHORT_TEXT),
            ]
        )
        db.commit()
        return doc_a.id, doc_b.id

    def test_full_pipeline_finds_direct_contradiction(self):
        llm = MockLLM()
        with Session(engine) as db:
            doc_a_id, doc_b_id = self._seed(db)

            claims_a = extract_claims(doc_a_id, db, llm)
            claims_b = extract_claims(doc_b_id, db, llm)
            self.assertEqual(len(claims_a), 1)
            self.assertEqual(len(claims_b), 1)

            contradictions = detect_contradictions([doc_a_id, doc_b_id], db)

            self.assertEqual(len(contradictions), 1)
            contra = contradictions[0]
            # RCT vs cohort with opposing directions -> METHODOLOGICAL, HIGH
            self.assertEqual(contra.contradiction_type, "METHODOLOGICAL")
            self.assertEqual(contra.severity, "HIGH")

            # Grading: RCT n=4200 outranks cohort n=890
            score_a, _ = grade_score(claims_a[0])
            score_b, _ = grade_score(claims_b[0])
            self.assertGreater(score_a, score_b)

    def test_rerun_is_idempotent(self):
        llm = MockLLM()
        with Session(engine) as db:
            doc_a_id, doc_b_id = self._seed(db)

            extract_claims(doc_a_id, db, llm)
            extract_claims(doc_b_id, db, llm)
            detect_contradictions([doc_a_id, doc_b_id], db)
            # Second run must replace, not duplicate
            extract_claims(doc_a_id, db, llm)
            extract_claims(doc_b_id, db, llm)
            contradictions = detect_contradictions([doc_a_id, doc_b_id], db)

            self.assertEqual(len(contradictions), 1)
            total_claims = db.query(MedicalClaim).count()
            self.assertEqual(total_claims, 2)


if __name__ == "__main__":
    unittest.main()
