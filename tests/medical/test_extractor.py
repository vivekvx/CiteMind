import os
import json
import tempfile

_TEMP_DIR = tempfile.TemporaryDirectory()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEMP_DIR.name}/test-extractor.db")

import unittest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.medical_claim import MedicalClaim
from backend.app.medical.extractor import extract_claims, _looks_medical

engine = create_engine(f"sqlite:///{_TEMP_DIR.name}/test-extractor.db")
Base.metadata.create_all(engine)

MOCK_LLM_RESPONSE = json.dumps({
    "claims": [
        {
            "drug": "Metformin",
            "condition": "Type 2 Diabetes",
            "outcome": "HbA1c reduction",
            "direction": "positive",
            "population": "Adults over 40",
            "study_type": "rct",
            "sample_size": 1200,
            "effect_size": "HR 0.82 (0.71-0.94)",
            "confidence": 0.92,
            "raw_text": "Metformin significantly reduced HbA1c in the RCT of 1200 patients."
        },
        {
            "drug": "Metformin",
            "condition": "Type 2 Diabetes",
            "outcome": "weight",
            "direction": "positive",
            "population": None,
            "study_type": "cohort",
            "sample_size": 300,
            "effect_size": None,
            "confidence": 0.3,
            "raw_text": "Some weight loss observed."
        },
    ]
})


class TestExtractor(unittest.TestCase):
    def setUp(self):
        with Session(engine) as db:
            db.query(MedicalClaim).delete()
            db.query(DocumentChunk).delete()
            db.query(Document).delete()
            db.commit()

    def test_extracts_claims_from_medical_chunk(self):
        mock_llm = MagicMock()
        mock_llm.complete.return_value = MOCK_LLM_RESPONSE

        with Session(engine) as db:
            doc = Document(title="study.pdf", content_hash="abc")
            db.add(doc)
            db.commit()
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                text="A randomized clinical trial of metformin treatment for diabetes patients showed significant HbA1c reduction.",
                embedding_json="[0.1]",
            )
            db.add(chunk)
            db.commit()

            claims = extract_claims(doc.id, db, mock_llm)

        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].drug, "Metformin")
        self.assertEqual(claims[0].direction, "positive")
        self.assertEqual(claims[0].study_type, "rct")
        self.assertEqual(claims[0].sample_size, 1200)
        mock_llm.complete.assert_called_once()

    def test_low_confidence_claims_filtered(self):
        mock_llm = MagicMock()
        mock_llm.complete.return_value = MOCK_LLM_RESPONSE

        with Session(engine) as db:
            doc = Document(title="study.pdf", content_hash="abc2")
            db.add(doc)
            db.commit()
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                text="A clinical trial of metformin drug treatment for diabetes patients showed some efficacy results.",
                embedding_json="[0.1]",
            )
            db.add(chunk)
            db.commit()

            claims = extract_claims(doc.id, db, mock_llm)

        self.assertTrue(all(c.confidence >= 0.4 for c in claims))

    def test_non_medical_chunks_skipped(self):
        mock_llm = MagicMock()

        with Session(engine) as db:
            doc = Document(title="readme.md", content_hash="def")
            db.add(doc)
            db.commit()
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                text="This is a readme file about software installation steps.",
                embedding_json="[0.1]",
            )
            db.add(chunk)
            db.commit()

            claims = extract_claims(doc.id, db, mock_llm)

        self.assertEqual(len(claims), 0)
        mock_llm.complete.assert_not_called()

    def test_idempotent_re_extraction(self):
        mock_llm = MagicMock()
        mock_llm.complete.return_value = MOCK_LLM_RESPONSE

        with Session(engine) as db:
            doc = Document(title="study.pdf", content_hash="idem")
            db.add(doc)
            db.commit()
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                text="A randomized clinical trial of metformin drug for diabetes patients with placebo control.",
                embedding_json="[0.1]",
            )
            db.add(chunk)
            db.commit()

            first = extract_claims(doc.id, db, mock_llm)
            second = extract_claims(doc.id, db, mock_llm)

        self.assertEqual(len(first), len(second))
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0].drug, "Metformin")

    def test_looks_medical_detection(self):
        self.assertTrue(_looks_medical("A randomized clinical trial of drug treatment"))
        self.assertTrue(_looks_medical("Patient mortality in cancer study"))
        self.assertFalse(_looks_medical("Software installation guide for developers"))
        self.assertFalse(_looks_medical("The weather is nice today"))


if __name__ == "__main__":
    unittest.main()
