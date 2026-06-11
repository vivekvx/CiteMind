# MedContradict — Implementation Plan

**Version:** 1.0  
**Date:** 2026-06-11  
**Status:** Approved  

---

## Overview

5-week plan. Each week = one shippable increment. Each phase builds on previous — don't start phase N+1 until phase N tests pass.

---

## Phase 1 — Fix Foundations (Week 1)

**Goal:** Real embeddings + Qdrant + Ollama running. Existing chat still works.

### Files to change

| File | Action | What |
|------|--------|------|
| `docker-compose.yml` | Edit | Add `qdrant` and `ollama` services |
| `backend/app/services/embeddings.py` | Rewrite | Replace SHA-256 fake with BGE-M3 via sentence-transformers |
| `backend/app/services/vector_store.py` | Rewrite | Replace in-memory list with Qdrant client |
| `backend/app/core/config.py` | Edit | Add `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `QDRANT_URL`, `LLM_PROVIDER` settings |
| `.env.example` | Edit | Add new env vars |
| `requirements.txt` | Edit | Add `sentence-transformers`, `qdrant-client`, `httpx` |

### New files

| File | What |
|------|------|
| `backend/app/services/llm_client.py` | LLMClient: Ollama → OpenAI → OpenRouter chain |
| `docker/ollama-init.sh` | Pull `llama3.2` model on first Ollama start |

### Verification

```bash
# Start infra
docker compose up qdrant ollama -d

# Upload sample doc
curl -X POST http://localhost:8000/documents/upload -F "file=@sample_docs/sample_ai_report.md"

# Chat still works
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "document_ids": [1]}'
```

Expected: real float embeddings in DB (not 64-char hex strings), Qdrant shows collection with vectors.

---

## Phase 2 — Claim Extraction (Week 2)

**Goal:** Upload paper → auto-extract structured claims → store in DB.

### New files

| File | What |
|------|------|
| `backend/app/medical/__init__.py` | Module init |
| `backend/app/medical/prompts.py` | `EXTRACTION_PROMPT`, `EXPLANATION_PROMPT`, `CONSENSUS_PROMPT` |
| `backend/app/medical/schemas.py` | `ClaimOut`, `ContradictionOut`, `ContradictionReport` Pydantic models |
| `backend/app/medical/grader.py` | `grade_score(claim) -> (int, str)` GRADE scoring |
| `backend/app/medical/extractor.py` | `extract_claims(document_id, db, llm) -> list[MedicalClaim]` |
| `backend/app/routes/medical.py` | `POST /medical/extract/{document_id}`, `GET /medical/claims/{document_id}` |
| `backend/app/models/medical_claim.py` | SQLAlchemy model |
| `alembic/versions/xxxx_add_medical_claims.py` | Migration: `medical_claims` table |

### Files to change

| File | Action | What |
|------|--------|------|
| `backend/app/main.py` | Edit | Include `medical` router |
| `backend/app/routes/documents.py` | Edit | Trigger `extract_claims` async after upload |

### Verification

```bash
curl -X POST http://localhost:8000/medical/extract/1
curl http://localhost:8000/medical/claims/1
```

Expected: JSON array with ≥3 claims, each with `drug`, `condition`, `outcome`, `direction`, `study_type`.

---

## Phase 3 — Contradiction Detection + Grading (Week 3)

**Goal:** Select 2+ docs → detect contradictions → return typed/severity-tagged pairs.

### New files

| File | What |
|------|------|
| `backend/app/medical/detector.py` | `detect_contradictions(doc_ids, db) -> list[Contradiction]` |
| `backend/app/models/contradiction.py` | SQLAlchemy model |
| `backend/app/models/analysis_job.py` | SQLAlchemy model |
| `alembic/versions/xxxx_add_contradictions_jobs.py` | Migration: `contradictions`, `analysis_jobs` tables |

### Files to change

| File | Action | What |
|------|--------|------|
| `backend/app/routes/medical.py` | Edit | Add `POST /medical/analyze`, `GET /medical/analyze/{job_id}` |

### Detection algorithm

```python
def detect_contradictions(document_ids: list[int], db: Session) -> list[Contradiction]:
    claims = db.scalars(
        select(MedicalClaim).where(MedicalClaim.document_id.in_(document_ids))
    ).all()

    groups: dict[tuple, list[MedicalClaim]] = defaultdict(list)
    for claim in claims:
        key = (claim.drug.lower().strip(),
               claim.condition.lower().strip(),
               claim.outcome.lower().strip())
        groups[key].append(claim)

    contradictions = []
    for group in groups.values():
        for i, a in enumerate(group):
            for b in group[i+1:]:
                if a.document_id == b.document_id:
                    continue
                if a.direction not in ("positive","negative"):
                    continue
                if b.direction not in ("positive","negative"):
                    continue
                if a.direction != b.direction:
                    contradictions.append(Contradiction(
                        claim_a_id=a.id, claim_b_id=b.id,
                        contradiction_type=_classify_type(a, b),
                        severity=_assess_severity(a, b),
                    ))
    db.add_all(contradictions)
    db.commit()
    return contradictions
```

### Verification

```bash
curl -X POST http://localhost:8000/medical/analyze \
  -H "Content-Type: application/json" -d '{"document_ids": [1, 2]}'

curl http://localhost:8000/medical/analyze/{job_id}
```

---

## Phase 4 — Explainer + UI (Week 4)

**Goal:** LLM-generated explanations + contradiction report page in frontend.

### New files

| File | What |
|------|------|
| `backend/app/medical/explainer.py` | `explain_contradiction(contra, db, llm) -> str` |
| `frontend/src/pages/Contradictions.tsx` | Main report page |
| `frontend/src/components/medical/DocumentSelector.tsx` | Multi-select uploaded docs |
| `frontend/src/components/medical/ContradictionPair.tsx` | Side-by-side claim cards |
| `frontend/src/components/medical/EvidenceBar.tsx` | Visual GRADE 1-5 bar |
| `frontend/src/api/medical.ts` | API client functions |

### Files to change

| File | Action | What |
|------|--------|------|
| `backend/app/routes/medical.py` | Edit | Add `GET /medical/contradictions/{job_id}` |
| `frontend/src/App.tsx` | Edit | Add `/contradictions` route |
| `frontend/src/components/Sidebar.tsx` | Edit | Add "Contradictions" nav link |

### UI flow

```
/contradictions:
  1. DocumentSelector — checkboxes for all uploaded docs
  2. "Analyze" button → POST /medical/analyze
  3. Poll GET /medical/analyze/{job_id} every 3s
  4. Render ContradictionReport:
     - Summary stats (X claims, Y contradictions found)
     - Per contradiction: ClaimA | ClaimB side-by-side with EvidenceBar
     - Explanation accordion (LLM explanation on expand)
     - Consensus statement at bottom
```

---

## Phase 5 — Polish + Eval (Week 5)

**Goal:** Tests, eval script, demo-ready.

### Tasks

1. Add 3 real medical papers to `tests/fixtures/medical/`
2. `scripts/eval_medcontradict.py` — precision/recall vs ground truth
3. Unit tests:
   - `tests/medical/test_extractor.py` — mock LLM, verify claim parsing
   - `tests/medical/test_detector.py` — synthetic claims, verify grouping
   - `tests/medical/test_grader.py` — GRADE table verification
4. `scripts/demo_medcontradict.sh` — one-command demo startup
5. Cache LLM responses by (chunk_hash, prompt_hash)
6. Batch BGE-M3 embeddings (32 chunks/batch)

---

## File Change Summary

### New files (20 total)

```
backend/app/medical/__init__.py
backend/app/medical/prompts.py
backend/app/medical/schemas.py
backend/app/medical/grader.py
backend/app/medical/extractor.py
backend/app/medical/detector.py
backend/app/medical/explainer.py
backend/app/routes/medical.py
backend/app/services/llm_client.py
backend/app/models/medical_claim.py
backend/app/models/contradiction.py
backend/app/models/analysis_job.py
alembic/versions/xxxx_add_medical_claims.py
alembic/versions/xxxx_add_contradictions_jobs.py
docker/ollama-init.sh
frontend/src/pages/Contradictions.tsx
frontend/src/api/medical.ts
frontend/src/components/medical/DocumentSelector.tsx
frontend/src/components/medical/ContradictionPair.tsx
frontend/src/components/medical/EvidenceBar.tsx
```

### Modified files (9 total)

```
docker-compose.yml
backend/app/services/embeddings.py
backend/app/services/vector_store.py
backend/app/core/config.py
backend/app/main.py
backend/app/routes/documents.py
requirements.txt
.env.example
frontend/src/App.tsx
```

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Ollama too slow | Batch by doc, show progress; OpenAI fallback |
| BGE-M3 download fails | Cache in Docker volume; fallback to `all-MiniLM-L6-v2` |
| LLM hallucinates claims | Confidence threshold (<0.5 discard) |
| Grouping misses drug synonyms | Fuzzy match in Phase 2; acceptable for MVP |
| Frontend routing conflicts | `/contradictions` is additive, no existing routes touched |
