# MedContradict — Technical Requirements Document

**Version:** 1.0  
**Date:** 2026-06-11  
**Status:** Approved  

---

## 1. Architecture Overview

```
                         ┌─────────────────────────────────────┐
                         │          FastAPI Backend             │
                         │                                      │
   Browser ─── React ──▶ │  /documents/*  /chat/*  /medical/*  │
                         │                                      │
                         │  ┌──────────────────────────────┐   │
                         │  │     medical/ module           │   │
                         │  │  extractor  detector  grader  │   │
                         │  └──────────────────────────────┘   │
                         │                                      │
                         │  embeddings ── vector_store ──────── ┼──▶ Qdrant
                         │  document_loader ── chunker          │
                         │  llm_client ──────────────────────── ┼──▶ Ollama / OpenAI
                         └─────────────────────────────────────┘
                                           │
                                     SQLite / Postgres
                                  (documents, chunks, claims,
                                   contradictions)
```

**Key principle:** `medical/` module is isolated. Zero changes to existing `/chat` or retrieval paths.

---

## 2. Stack Decisions

| Layer | Choice | Reason |
|-------|--------|--------|
| Parser | MarkItDown (current) → Docling (Phase 2) | MarkItDown already wired; Docling adds OCR for medical PDFs |
| Chunker | `chunk_markdown()` (already built) | Heading-aware, keeps section context |
| Embeddings | `sentence-transformers` BGE-M3 | Local, free, best-in-class for scientific text |
| Vector DB | Qdrant (Docker) | Already in settings; replaces fake in-memory store |
| LLM primary | Ollama `llama3.2` | Local, free, zero API cost |
| LLM fallback | OpenAI `gpt-4o-mini` → OpenRouter | Budget upgrade path |
| Claim DB | SQLite (dev) / Postgres (prod) via SQLAlchemy | Already wired |
| Reranker | FlashRank (optional, already in requirements-optional.txt) | Improves claim retrieval |

---

## 3. Data Models

### 3.1 `MedicalClaim`

```python
class MedicalClaim(Base):
    __tablename__ = "medical_claims"

    id: int (PK)
    document_id: int (FK → documents.id, CASCADE DELETE)
    chunk_index: int              # source chunk for traceability
    drug: str                     # normalized to lowercase
    condition: str                # normalized to lowercase
    outcome: str                  # e.g. "mortality", "HbA1c reduction"
    direction: str                # "positive" | "negative" | "neutral" | "unclear"
    population: str | None        # e.g. "T2DM patients with HFrEF"
    study_type: str               # meta_analysis|rct|cohort|case_control|case_series|unknown
    sample_size: int | None
    effect_size: str | None       # raw text e.g. "HR 0.82 (0.71-0.94)"
    confidence: float             # 0.0-1.0 LLM self-reported confidence
    raw_text: str                 # verbatim sentence(s) from paper
    created_at: datetime
```

### 3.2 `Contradiction`

```python
class Contradiction(Base):
    __tablename__ = "contradictions"

    id: int (PK)
    claim_a_id: int (FK → medical_claims.id)
    claim_b_id: int (FK → medical_claims.id)
    contradiction_type: str       # DIRECT|PARTIAL|METHODOLOGICAL|TEMPORAL
    severity: str                 # HIGH|MEDIUM|LOW
    explanation: str | None       # LLM-generated explanation (cached)
    consensus: str | None         # LLM-generated consensus statement (cached)
    created_at: datetime
```

### 3.3 `AnalysisJob`

```python
class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: str (UUID PK)
    document_ids: str             # JSON array of ints
    status: str                   # pending|running|done|failed
    result_json: str | None       # full ContradictionReport as JSON
    error: str | None
    created_at: datetime
    completed_at: datetime | None
```

---

## 4. Module Structure

```
backend/app/medical/
├── __init__.py
├── extractor.py          # claim extraction via LLM
├── detector.py           # contradiction detection logic
├── grader.py             # GRADE evidence scoring
├── explainer.py          # LLM contradiction explanation + consensus
├── schemas.py            # Pydantic models: ClaimOut, ContradictionOut, ReportOut
└── prompts.py            # prompt templates (extraction, explanation, consensus)
```

---

## 5. API Endpoints

### 5.1 Claim Extraction (auto-triggered on upload, also manual)

```
POST /medical/extract/{document_id}
Response: { claims: ClaimOut[], count: int }
```

### 5.2 Start Contradiction Analysis

```
POST /medical/analyze
Body: { document_ids: int[] }
Response: { job_id: str }
```

### 5.3 Poll Job Status

```
GET /medical/analyze/{job_id}
Response: { status: str, result?: ContradictionReport }
```

### 5.4 Get Claims for Document

```
GET /medical/claims/{document_id}
Response: ClaimOut[]
```

### 5.5 Get All Contradictions for Job

```
GET /medical/contradictions/{job_id}
Response: ContradictionOut[]
```

---

## 6. Pydantic Schemas

```python
class ClaimOut(BaseModel):
    id: int
    document_id: int
    drug: str
    condition: str
    outcome: str
    direction: str
    study_type: str
    grade_score: int              # 1-5 from grader
    evidence_label: str           # "Strong" | "Moderate" | "Low" | "Very Low"
    raw_text: str
    confidence: float

class ContradictionOut(BaseModel):
    id: int
    claim_a: ClaimOut
    claim_b: ClaimOut
    contradiction_type: str
    severity: str
    explanation: str | None
    consensus: str | None

class ContradictionReport(BaseModel):
    job_id: str
    document_ids: list[int]
    claims_by_document: dict[int, list[ClaimOut]]
    contradictions: list[ContradictionOut]
    total_claims: int
    total_contradictions: int
    generated_at: str
```

---

## 7. LLM Client Design

```python
# backend/app/services/llm_client.py (new file)

class LLMClient:
    """Single provider chain: Ollama → OpenAI → OpenRouter."""

    def complete(self, prompt: str, system: str = "", json_mode: bool = False) -> str: ...
    def _try_ollama(self, ...) -> str | None: ...
    def _try_openai(self, ...) -> str | None: ...
    def _try_openrouter(self, ...) -> str | None: ...
```

Config (via `settings`):
- `OLLAMA_BASE_URL` = `http://localhost:11434`
- `OLLAMA_MODEL` = `llama3.2`
- `OPENAI_API_KEY` = optional
- `OPENROUTER_API_KEY` = optional
- `LLM_PROVIDER` = `auto` | `ollama` | `openai` | `openrouter`

---

## 8. Claim Extraction Algorithm

```
for each document_id in request.document_ids:
    chunks = get_chunks(document_id)
    for each chunk:
        if chunk appears medical (drug/disease keywords):
            prompt = EXTRACTION_PROMPT.format(chunk_text=chunk.text)
            response = llm.complete(prompt, json_mode=True)
            claims = parse_claims(response)
            save_claims(claims, document_id, chunk.chunk_index)
```

Extraction prompt returns JSON array of claims. Uses structured output / JSON mode where available.

---

## 9. Contradiction Detection Algorithm

```
claims = get_all_claims(document_ids)
groups = group_by(claims, key=(normalize(drug), normalize(condition), normalize(outcome)))

for each group with >=2 claims from different documents:
    for each pair (claim_a, claim_b):
        if claim_a.direction != claim_b.direction:
            type = classify_type(claim_a, claim_b)
            severity = assess_severity(claim_a, claim_b)
            save_contradiction(claim_a, claim_b, type, severity)
```

`classify_type` rules:
- Same drug+condition+outcome, opposite direction → `DIRECT`
- Same drug+condition, different outcome → `PARTIAL`
- Same conclusion, different study design → `METHODOLOGICAL`
- Studies span >5 years apart → `TEMPORAL`

---

## 10. GRADE Evidence Scoring

```python
GRADE_SCORES = {
    "meta_analysis": 5,
    "rct": 4,
    "cohort": 3,
    "case_control": 2,
    "case_series": 1,
    "unknown": 1,
}

def grade_score(claim: MedicalClaim) -> tuple[int, str]:
    base = GRADE_SCORES.get(claim.study_type, 1)
    if claim.sample_size and claim.sample_size >= 1000 and base < 5:
        base = min(base + 1, 5)
    labels = {5: "Strong", 4: "Moderate", 3: "Low", 2: "Very Low", 1: "Very Low"}
    return base, labels.get(base, "Very Low")
```

---

## 11. Infrastructure

### Docker Compose additions

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["qdrant_data:/qdrant/storage"]

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: ["ollama_data:/root/.ollama"]
```

### Embedding service migration

Replace fake SHA-256 embeddings in `backend/app/services/embeddings.py` with BGE-M3:

```python
from sentence_transformers import SentenceTransformer

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-m3")
    return _model

def embed_chunks(chunks: list[str]) -> list[list[float]]:
    return _get_model().encode(chunks, normalize_embeddings=True).tolist()
```

---

## 12. New Dependencies

Add to `requirements.txt`:
```
sentence-transformers>=2.7.0
qdrant-client>=1.9.0
httpx>=0.27.0
```

Add to `requirements-optional.txt`:
```
docling>=2.0.0
```

Add to `.env.example`:
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
LLM_PROVIDER=auto
OPENAI_API_KEY=
OPENROUTER_API_KEY=
```

---

## 13. DB Migration

New Alembic migration: `add_medical_claims_contradictions_analysis_jobs`

Tables: `medical_claims`, `contradictions`, `analysis_jobs`

Indexes:
- `medical_claims(document_id)`
- `medical_claims(drug, condition, outcome)` — grouping queries
- `contradictions(claim_a_id, claim_b_id)`

---

## 14. Frontend Changes

New page: `frontend/src/pages/Contradictions.tsx`

Components needed:
- `DocumentSelector` — multi-select from uploaded docs
- `ContradictionReport` — main report view
- `ClaimCard` — single claim with GRADE bar
- `ContradictionPair` — side-by-side opposing claims
- `EvidenceBar` — visual 1-5 GRADE strength indicator

---

## 15. Performance Targets

| Operation | Target |
|-----------|--------|
| Claim extraction per chunk | <3s (Ollama local) |
| Full extraction (50-chunk paper) | <60s |
| Contradiction detection (3 papers) | <5s (pure algorithm) |
| Explanation per pair | <5s (Ollama local) |
| Full analysis job (3 papers) | <90s end-to-end |
| BGE-M3 embed 100 chunks | <10s (CPU) |

---

## 16. Error Handling

- Ollama unavailable → fallback to OpenAI if key present, else `503` with clear message
- LLM returns malformed JSON → retry once with stricter prompt, then skip chunk
- 0 claims extracted → document flagged `non_medical`, skip in analysis
- Analysis job fails → status = `failed`, error stored in `analysis_jobs.error`
