import os
import tempfile

_TEMP_DIR = tempfile.TemporaryDirectory()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEMP_DIR.name}/test-detector.db")

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.medical_claim import MedicalClaim
from backend.app.models.contradiction import Contradiction
from backend.app.models.document import Document
from backend.app.medical.detector import detect_contradictions

engine = create_engine(f"sqlite:///{_TEMP_DIR.name}/test-detector.db")
Base.metadata.create_all(engine)


def _make_claim(db: Session, **kwargs) -> MedicalClaim:
    defaults = dict(
        document_id=1,
        chunk_index=0,
        drug="aspirin",
        condition="heart disease",
        outcome="mortality",
        direction="positive",
        study_type="rct",
        sample_size=500,
        confidence=0.9,
        raw_text="Aspirin reduced mortality in heart disease patients.",
    )
    defaults.update(kwargs)
    claim = MedicalClaim(**defaults)
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


class TestDetector(unittest.TestCase):
    def setUp(self):
        with Session(engine) as db:
            db.query(Contradiction).delete()
            db.query(MedicalClaim).delete()
            db.query(Document).delete()
            db.commit()

    def test_opposite_directions_creates_contradiction(self):
        with Session(engine) as db:
            doc = Document(title="doc1.pdf", content_hash="h1")
            doc2 = Document(title="doc2.pdf", content_hash="h2")
            db.add_all([doc, doc2])
            db.commit()
            _make_claim(db, document_id=doc.id, direction="positive")
            _make_claim(db, document_id=doc2.id, direction="negative")

            result = detect_contradictions([doc.id, doc2.id], db)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].contradiction_type, "DIRECT")

    def test_same_direction_no_contradiction(self):
        with Session(engine) as db:
            doc = Document(title="doc1.pdf", content_hash="h1")
            doc2 = Document(title="doc2.pdf", content_hash="h2")
            db.add_all([doc, doc2])
            db.commit()
            _make_claim(db, document_id=doc.id, direction="positive")
            _make_claim(db, document_id=doc2.id, direction="positive")

            result = detect_contradictions([doc.id, doc2.id], db)

        self.assertEqual(len(result), 0)

    def test_same_document_no_contradiction(self):
        with Session(engine) as db:
            doc = Document(title="doc1.pdf", content_hash="h1")
            db.add(doc)
            db.commit()
            _make_claim(db, document_id=doc.id, direction="positive", chunk_index=0)
            _make_claim(db, document_id=doc.id, direction="negative", chunk_index=1)

            result = detect_contradictions([doc.id], db)

        self.assertEqual(len(result), 0)

    def test_methodological_type_when_different_study_types(self):
        with Session(engine) as db:
            doc = Document(title="doc1.pdf", content_hash="h1")
            doc2 = Document(title="doc2.pdf", content_hash="h2")
            db.add_all([doc, doc2])
            db.commit()
            _make_claim(db, document_id=doc.id, direction="positive", study_type="meta_analysis")
            _make_claim(db, document_id=doc2.id, direction="negative", study_type="case_series")

            result = detect_contradictions([doc.id, doc2.id], db)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].contradiction_type, "METHODOLOGICAL")
        self.assertEqual(result[0].severity, "HIGH")

    def test_severity_low_when_both_low_evidence(self):
        with Session(engine) as db:
            doc = Document(title="doc1.pdf", content_hash="h1")
            doc2 = Document(title="doc2.pdf", content_hash="h2")
            db.add_all([doc, doc2])
            db.commit()
            _make_claim(db, document_id=doc.id, direction="positive", study_type="case_series")
            _make_claim(db, document_id=doc2.id, direction="negative", study_type="unknown")

            result = detect_contradictions([doc.id, doc2.id], db)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].severity, "LOW")

    def test_neutral_direction_ignored(self):
        with Session(engine) as db:
            doc = Document(title="doc1.pdf", content_hash="h1")
            doc2 = Document(title="doc2.pdf", content_hash="h2")
            db.add_all([doc, doc2])
            db.commit()
            _make_claim(db, document_id=doc.id, direction="neutral")
            _make_claim(db, document_id=doc2.id, direction="negative")

            result = detect_contradictions([doc.id, doc2.id], db)

        self.assertEqual(len(result), 0)

    def test_different_drug_no_contradiction(self):
        with Session(engine) as db:
            doc = Document(title="doc1.pdf", content_hash="h1")
            doc2 = Document(title="doc2.pdf", content_hash="h2")
            db.add_all([doc, doc2])
            db.commit()
            _make_claim(db, document_id=doc.id, direction="positive", drug="aspirin")
            _make_claim(db, document_id=doc2.id, direction="negative", drug="metformin")

            result = detect_contradictions([doc.id, doc2.id], db)

        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
