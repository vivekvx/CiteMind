from __future__ import annotations

import os
import tempfile

_TEMP_DIR = tempfile.TemporaryDirectory()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEMP_DIR.name}/test-grader.db")

import unittest
from types import SimpleNamespace

from backend.app.medical.grader import GRADE_SCORES, grade_score


def _claim(study_type: str = "unknown", sample_size: int | None = None):
    return SimpleNamespace(study_type=study_type, sample_size=sample_size)


class TestGradeScore(unittest.TestCase):
    def test_all_study_types_have_expected_base_scores(self):
        expected = {
            "meta_analysis": 5,
            "rct": 4,
            "cohort": 3,
            "case_control": 2,
            "case_series": 1,
            "unknown": 1,
        }
        for study_type, score in expected.items():
            result_score, _ = grade_score(_claim(study_type))
            self.assertEqual(result_score, score, f"{study_type} should be {score}")

    def test_sample_size_bonus_adds_one(self):
        score, label = grade_score(_claim("cohort", 1500))
        self.assertEqual(score, 4)
        self.assertEqual(label, "Moderate")

    def test_sample_size_bonus_caps_at_5(self):
        score, _ = grade_score(_claim("meta_analysis", 5000))
        self.assertEqual(score, 5)

    def test_no_bonus_under_1000(self):
        score, _ = grade_score(_claim("cohort", 999))
        self.assertEqual(score, 3)

    def test_no_bonus_when_sample_size_none(self):
        score, _ = grade_score(_claim("rct", None))
        self.assertEqual(score, 4)

    def test_label_mapping(self):
        self.assertEqual(grade_score(_claim("meta_analysis"))[1], "Strong")
        self.assertEqual(grade_score(_claim("rct"))[1], "Moderate")
        self.assertEqual(grade_score(_claim("cohort"))[1], "Low")
        self.assertEqual(grade_score(_claim("case_control"))[1], "Very Low")
        self.assertEqual(grade_score(_claim("case_series"))[1], "Very Low")

    def test_unknown_study_type_defaults_to_1(self):
        score, label = grade_score(_claim("something_new"))
        self.assertEqual(score, 1)
        self.assertEqual(label, "Very Low")


if __name__ == "__main__":
    unittest.main()
