#!/usr/bin/env python3
"""MedContradict evaluation script.

Uploads fixture papers, runs extraction + contradiction detection,
and reports precision/recall against expected ground truth.

Usage:
    python scripts/eval_medcontradict.py [--api-url http://localhost:8001]

Requires the backend server to be running.
"""
import argparse
import glob
import os
import sys

import httpx

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "medical")

GROUND_TRUTH = {
    "expected_drugs": {"atorvastatin", "metformin"},
    "expected_contradictions": [
        {
            "drug": "atorvastatin",
            "condition_contains": "cardiovascular",
            "directions": {"positive", "negative"},
        },
    ],
}


def upload_fixture(client: httpx.Client, api_url: str, path: str) -> int:
    filename = os.path.basename(path)
    with open(path, "rb") as f:
        resp = client.post(
            f"{api_url}/documents/upload",
            files={"file": (filename, f, "text/markdown")},
            timeout=60,
        )
    resp.raise_for_status()
    doc_id = resp.json()["id"]
    print(f"  Uploaded {filename} -> doc_id={doc_id}")
    return doc_id


def extract_claims(client: httpx.Client, api_url: str, doc_id: int) -> list:
    resp = client.post(f"{api_url}/medical/extract/{doc_id}", timeout=120)
    resp.raise_for_status()
    count = resp.json()["count"]
    print(f"  Extracted {count} claims from doc {doc_id}")

    resp = client.get(f"{api_url}/medical/claims/{doc_id}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def run_analysis(client: httpx.Client, api_url: str, doc_ids: list) -> dict:
    resp = client.post(
        f"{api_url}/medical/analyze",
        json={"document_ids": doc_ids},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()


def evaluate_claims(all_claims: list) -> dict:
    found_drugs = {c["drug"].lower().strip() for c in all_claims}
    expected_drugs = {d.lower() for d in GROUND_TRUTH["expected_drugs"]}

    tp = found_drugs & expected_drugs
    precision = len(tp) / len(found_drugs) if found_drugs else 0
    recall = len(tp) / len(expected_drugs) if expected_drugs else 0

    return {
        "found_drugs": found_drugs,
        "expected_drugs": expected_drugs,
        "drug_precision": precision,
        "drug_recall": recall,
        "total_claims": len(all_claims),
    }


def evaluate_contradictions(report: dict) -> dict:
    contras = report.get("contradictions", [])
    expected = GROUND_TRUTH["expected_contradictions"]

    matched = 0
    for exp in expected:
        for c in contras:
            a_drug = c["claim_a"]["drug"].lower()
            b_drug = c["claim_b"]["drug"].lower()
            a_dir = c["claim_a"]["direction"]
            b_dir = c["claim_b"]["direction"]
            if (
                exp["drug"].lower() in (a_drug, b_drug)
                and {a_dir, b_dir} == exp["directions"]
            ):
                matched += 1
                break

    precision = matched / len(contras) if contras else 0
    recall = matched / len(expected) if expected else 0

    return {
        "total_contradictions": len(contras),
        "expected_contradictions": len(expected),
        "matched": matched,
        "contradiction_precision": precision,
        "contradiction_recall": recall,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate MedContradict pipeline")
    parser.add_argument("--api-url", default="http://localhost:8001")
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    client = httpx.Client()

    print("MedContradict Evaluation")
    print(f"API: {api_url}")
    print(f"Fixtures: {FIXTURES_DIR}")
    print()

    fixtures = sorted(glob.glob(os.path.join(FIXTURES_DIR, "*.md")))
    if not fixtures:
        print("ERROR: No fixture files found")
        sys.exit(1)

    print(f"Found {len(fixtures)} fixture papers")
    print()

    print("1. Uploading papers...")
    doc_ids = []
    for path in fixtures:
        doc_id = upload_fixture(client, api_url, path)
        doc_ids.append(doc_id)
    print()

    print("2. Extracting claims...")
    all_claims = []
    for doc_id in doc_ids:
        claims = extract_claims(client, api_url, doc_id)
        all_claims.extend(claims)
    print()

    print("3. Evaluating claim extraction...")
    claim_eval = evaluate_claims(all_claims)
    print(f"  Total claims: {claim_eval['total_claims']}")
    print(f"  Found drugs: {claim_eval['found_drugs']}")
    print(f"  Drug precision: {claim_eval['drug_precision']:.2f}")
    print(f"  Drug recall: {claim_eval['drug_recall']:.2f}")
    print()

    if len(doc_ids) >= 2:
        print("4. Running contradiction analysis...")
        report = run_analysis(client, api_url, doc_ids)
        print(f"  Job: {report['job_id'][:8]}")
        print()

        print("5. Evaluating contradictions...")
        contra_eval = evaluate_contradictions(report)
        print(f"  Total contradictions found: {contra_eval['total_contradictions']}")
        print(f"  Expected contradictions: {contra_eval['expected_contradictions']}")
        print(f"  Matched: {contra_eval['matched']}")
        print(f"  Contradiction precision: {contra_eval['contradiction_precision']:.2f}")
        print(f"  Contradiction recall: {contra_eval['contradiction_recall']:.2f}")
        print()

        print("=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"  Claim extraction drug recall: {claim_eval['drug_recall']:.0%}")
        print(f"  Contradiction recall: {contra_eval['contradiction_recall']:.0%}")

        passed = claim_eval["drug_recall"] >= 0.5 and contra_eval["contradiction_recall"] >= 0.5
        print(f"  Overall: {'PASS' if passed else 'NEEDS IMPROVEMENT'}")
        sys.exit(0 if passed else 1)
    else:
        print("Not enough documents for contradiction analysis (need >= 2)")
        sys.exit(1)


if __name__ == "__main__":
    main()
