# CiteMind

CiteMind is a citation-first AI research assistant for document Q&A, research summaries, and lightweight RAG evaluation.

## Problem Statement

Researchers need fast answers from documents, but answers are only useful when they can be traced back to supporting evidence. CiteMind focuses on uploads, grounded answers, citations, retrieved chunks, and evaluation scores.

## Current Phase

CiteMind is currently in a local MVP/demo phase. The app supports the full loop of uploading a document, asking questions over the selected document, receiving cited answers, and running evaluation scores from the UI.

The backend defaults to SQLite and an in-memory vector store hydrated from persisted chunks and deterministic local embeddings, so the demo can run without external services. OpenAI is optional: when `OPENAI_API_KEY` is configured, CiteMind uses OpenAI for answer synthesis and judge-style evaluation; otherwise it falls back to local extractive answers and heuristic scoring.

## Features

- Upload text-based research documents.
- List and select uploaded documents in the frontend.
- Ask research questions over selected document content.
- Detect common research intents such as summaries, important topics, study notes, flashcards, definitions, comparisons, and normal Q&A.
- Return cited answers with retrieved chunks.
- Log queries and save evaluation results.
- Run RAG evaluation with faithfulness, answer relevance, context relevance, and citation coverage scores.
- Use OpenAI answer generation and judge scoring when `OPENAI_API_KEY` exists, with local fallbacks for demos.

## Architecture

- Frontend: Next.js single-page UI for upload, document selection, Q&A, citations, and evaluation score cards.
- Backend: FastAPI API service with document, query, evaluation, and health routes.
- Database: SQLite by default for local development; Docker Compose also provisions PostgreSQL for containerized runs.
- Retrieval: In-memory vector store hydrated from SQLite chunks and stored deterministic embeddings in the current MVP phase.
- Answering: Intent-aware research agent with optional OpenAI synthesis and local extractive fallback.
- Evaluation: OpenAI judge prompts when configured, local heuristics otherwise.

## Tech Stack

- FastAPI
- SQLAlchemy
- SQLite
- PostgreSQL via Docker Compose
- Next.js
- TypeScript
- Tailwind CSS
- Docker Compose

## Setup

```bash
cd /Users/vivek/CiteMind/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

```bash
cd /Users/vivek/CiteMind/frontend
npm install
```

## Run Locally

Recommended one-command local run:

```bash
cd /Users/vivek/CiteMind
./dev.sh
```

This starts the backend on `http://localhost:8001` and the frontend on
`http://localhost:3001`. Press `Ctrl+C` in the same terminal to stop both.

Manual run commands:

```bash
cd /Users/vivek/CiteMind
backend/.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001
```

```bash
cd /Users/vivek/CiteMind/frontend
npm run dev
```

## Env Vars

Copy `.env.example` to `.env` and fill values as needed.

```bash
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
DATABASE_URL=sqlite:///./citemind.db
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=citemind_chunks
NEXT_PUBLIC_API_URL=http://localhost:8001
```

Create `frontend/.env.local` for local frontend runs:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
```

Do not commit real `.env` files or API keys.

## API Endpoints

- `GET /health`
- `GET /health/llm`
- `POST /documents/upload`
- `GET /documents`
- `DELETE /documents/{document_id}`
- `POST /query`
- `POST /evals/run`

`GET /health/llm` verifies whether OpenAI chat synthesis is configured and
reachable. If it returns an error such as `insufficient_quota (HTTP 429)`, the
backend is reaching OpenAI but the account needs quota or billing fixed before
synthesized answers can work.

## Demo Workflow

1. Start the backend API.
2. Start the frontend.
3. Upload `sample_docs/sample_ai_report.md`.
4. Ask a research question, summary request, topic request, study-note prompt, or flashcard prompt.
5. Review the answer, citations, and retrieved chunks.
6. Run evaluation and review the score cards.

## Manual Quality Checklist

Use this checklist after OpenAI API quota is available:

- Upload one PDF and ask `Give me exactly 10 important topics from this PDF.`
  The answer should be numbered, cited, and free of copyright, praise, contact
  info, boilerplate, or code-only chunks.
- Ask a follow-up such as `Make study notes from this PDF.` without reuploading.
  The same active document should be used.
- Ask a narrow question such as `What is this concept used for?` The answer
  should be concise and should not force a 10-point structure.
- Upload two documents, select each one in turn, and ask `Give me 5 key points.`
  Retrieved chunks and citations should stay scoped to the selected document.

When `/health/llm` reports `ok: false`, the UI shows that CiteMind is using
local fallback answers. This is useful for development, but final answer quality
should be judged after LLM synthesis is available.

## Evaluation Metrics

- `faithfulness_score`: whether the answer is supported by retrieved context
- `answer_relevance_score`: whether the answer addresses the user query
- `context_relevance_score`: whether retrieved chunks match the query
- `citation_coverage_score`: whether answer claims include bracket-style citations

For structured summary/topic answers, local heuristic evaluation also checks
numbered structure, requested count, citation coverage per numbered point, and
obvious noisy boilerplate.

## Local Limits

- OpenAI quota must be active for synthesized LLM answers and judge scoring.
- SQLite is the default local database.
- Document chunks and deterministic embeddings are persisted locally; the
  in-memory vector store is hydrated from SQLite on backend startup.
- Exact duplicate uploads are reused by file content hash.
- Schema changes use a small local SQLite upgrade helper, not Alembic yet.
- Qdrant settings are present for future integration; local development currently
  uses SQLite plus the hydrated in-memory vector store.

## Checks

```bash
cd /Users/vivek/CiteMind
PYTHONPYCACHEPREFIX=/private/tmp/citemind-pycache backend/.venv/bin/python -m compileall backend/__init__.py backend/app
backend/.venv/bin/python -m unittest backend.app.tests.test_regressions
backend/.venv/bin/python -c "from backend.app.main import app; print([route.path for route in app.routes])"
```

```bash
cd /Users/vivek/CiteMind/frontend
npm run build
```

## Resume Bullets

- Built a full-stack citation-first research assistant with FastAPI, Next.js, SQLAlchemy, and Tailwind CSS.
- Implemented document upload, chunking, deterministic local retrieval, citation display, query logging, and RAG evaluation.
- Added an intent-aware research agent for summaries, topics, study notes, flashcards, definitions, comparisons, and Q&A.
- Added local heuristic evaluation fallback with optional OpenAI answer generation and judge-based scoring.
- Containerized frontend, backend, database, and vector store with Docker Compose.

## Future Improvements

- Persist vector embeddings in Qdrant
- Add migrations with Alembic
- Expand automated tests and CI
