# CiteMind / MedContradict — AI Coding Guide

## Commands

```bash
# Backend
backend/.venv/bin/python -m pytest
backend/.venv/bin/pip install -r requirements.txt
uvicorn backend.app.main:app --reload

# Frontend
cd frontend && npm run dev

# Infra
docker compose up qdrant ollama -d
```

## Architecture

```
backend/app/
├── core/       config, rate limiting
├── db/         SQLAlchemy setup
├── models/     ORM models
├── routes/     FastAPI routers (documents, chat, eval, medical)
├── services/   embeddings, vector_store, document_loader, chunker, llm_client
├── schemas/    Pydantic schemas
└── medical/    MedContradict module (isolated)
```

## Module Boundaries

- `medical/` has no imports from `routes/` — only from `services/` and `models/`
- `routes/chat.py` and `routes/documents.py` must not import from `medical/`
- `medical/` calls `llm_client.py` — never calls OpenAI/Ollama SDK directly
- Claim extraction is idempotent — re-running on same doc replaces existing claims

## Constraints

- Python binary: always `backend/.venv/bin/python` and `backend/.venv/bin/pip`
- Don't rewrite working files outside your task scope
- No auth/session/multi-tenancy unless explicitly requested
- Don't add features beyond the current task phase
- Don't delete LICENSE

## LLM Provider Chain

`llm_client.py` tries: Ollama → OpenAI → OpenRouter.
Controlled by `LLM_PROVIDER` env var (`auto` | `ollama` | `openai` | `openrouter`).

## Embeddings

`embeddings.py` uses BGE-M3 via `sentence-transformers`. Model cached in `_model` global.
Never use SHA-256 hashing as fake embeddings.

## Vector Store

Qdrant at `QDRANT_URL` (default `http://localhost:6333`). Collection: `citemind_chunks`.
Always go through `vector_store.py` — don't call `qdrant_client` directly from routes.

## Medical Module (MedContradict)

```
medical/
├── prompts.py    extraction + explanation prompt templates
├── extractor.py  extract_claims(document_id, db, llm)
├── detector.py   detect_contradictions(doc_ids, db)
├── grader.py     grade_score(claim) -> (int, str)
├── explainer.py  explain_contradiction(contra, db, llm)
└── schemas.py    ClaimOut, ContradictionOut, ContradictionReport
```

GRADE: `meta_analysis=5, rct=4, cohort=3, case_control=2, case_series=1`
Contradiction types: `DIRECT | PARTIAL | METHODOLOGICAL | TEMPORAL`

## Chunking

- Markdown/PDF via markitdown → `chunk_markdown()`
- Plain text → `chunk_text()`

## Database

SQLAlchemy + Alembic. Models in `backend/app/models/`.
Always create Alembic migration for schema changes.

## Docs

- PRD: `docs/superpowers/specs/2026-06-11-medcontradict-prd.md`
- TRD: `docs/superpowers/specs/2026-06-11-medcontradict-trd.md`
- Plan: `docs/superpowers/specs/2026-06-11-medcontradict-implementation-plan.md`
