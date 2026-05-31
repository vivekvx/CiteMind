# CiteMind

CiteMind is a citation-first AI research assistant for document Q&A, research summaries, and lightweight RAG evaluation.

## Problem Statement

Researchers need fast answers from documents, but answers are only useful when they can be traced back to supporting evidence. CiteMind focuses on uploads, grounded answers, citations, retrieved chunks, and evaluation scores.

## Current Phase

CiteMind is currently in a local MVP/demo phase. The app supports the full loop of uploading a document, asking questions over the selected document, receiving cited answers, and running evaluation scores from the UI.

The backend defaults to SQLite and an in-memory vector store hydrated from persisted chunks and deterministic local embeddings, so the demo can run without external services. LLM synthesis is optional: when `LLM_API_KEY` is configured, CiteMind uses the configured OpenAI-compatible chat provider for answer synthesis and judge-style evaluation. If `LLM_*` is blank, the existing `OPENAI_*` settings still work. If no provider key is configured, CiteMind falls back to local extractive answers and heuristic scoring.

## Features

- Upload text-based research documents.
- List and select uploaded documents in the frontend.
- Ask research questions over selected document content.
- Detect common research intents such as summaries, important topics, study notes, flashcards, definitions, comparisons, and normal Q&A.
- Return cited answers with retrieved chunks.
- Log queries and save evaluation results.
- Run RAG evaluation with faithfulness, answer relevance, context relevance, and citation coverage scores.
- Use OpenAI-compatible answer generation and judge scoring when an LLM provider key exists, with local fallbacks for demos.

## Architecture

- Frontend: Next.js single-page UI for upload, document selection, Q&A, citations, and evaluation score cards.
- Backend: FastAPI API service with document, query, evaluation, and health routes.
- Database: SQLite by default for local and Docker Compose runs.
- Retrieval: In-memory vector store hydrated from SQLite chunks and stored deterministic embeddings in the current MVP phase.
- Answering: Intent-aware research agent with optional OpenAI-compatible synthesis and local extractive fallback.
- Evaluation: LLM judge prompts when configured, local heuristics otherwise.

## Tech Stack

- FastAPI
- SQLAlchemy
- SQLite
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

Docker Compose uses the same local MVP ports and SQLite-backed persistence:

```bash
cd /Users/vivek/CiteMind
docker compose up --build
```

Open the app at `http://localhost:3001`; backend docs are available at
`http://localhost:8001/docs`.

## Env Vars

Copy `.env.example` to `.env` and fill values as needed.

```bash
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
LLM_API_KEY=
LLM_BASE_URL=
LLM_CHAT_MODEL=
DATABASE_URL=sqlite:///./citemind.db
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=citemind_chunks
RETRIEVAL_MODE=vector
PAGE_INDEX_MIN_CHUNKS=8
NEXT_PUBLIC_API_URL=http://localhost:8001
BACKEND_API_URL=
```

Create `frontend/.env.local` for local frontend runs:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
```

For Vercel frontend deployments, set `NEXT_PUBLIC_API_URL=/api` and
`BACKEND_API_URL` to the deployed backend URL so Next.js rewrites `/api/*`
requests to FastAPI.

Do not commit real `.env` files or API keys.

`LLM_*` settings are optional OpenAI-compatible provider overrides. They take
precedence over `OPENAI_*` when present. For example, DeepSeek-style local
testing can use:

```bash
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=<your-provider-key>
LLM_CHAT_MODEL=deepseek-chat
```

When `LLM_*` is blank, CiteMind uses the existing `OPENAI_*` settings.
Restart the backend after changing `.env` because settings are loaded at
process startup.

## API Endpoints

- `GET /health`
- `GET /health/llm`
- `POST /documents/upload`
- `POST /documents/demo/reset`
- `GET /documents`
- `DELETE /documents/{document_id}`
- `POST /query`
- `POST /evals/run`

`GET /health/llm` verifies whether the configured OpenAI-compatible chat
provider is configured and reachable. If the backend is using OpenAI and this
returns an error such as `insufficient_quota (HTTP 429)`, the account needs
quota or billing fixed before synthesized answers can work. For other providers,
check the provider key, base URL, model name, and rate limits.

## Demo Workflow

1. Start the backend API.
2. Start the frontend.
3. Upload `sample_docs/sample_ai_report.md`.
4. Ask a research question, summary request, topic request, study-note prompt, or flashcard prompt.
5. Review the answer, citations, and retrieved chunks.
6. Run evaluation and review the score cards.

## Manual Quality Checklist

Use this checklist after `/health/llm` reports that an LLM provider is reachable:

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

- A reachable LLM provider is required for synthesized answers and judge scoring.
- SQLite is the default local database.
- Document chunks and deterministic embeddings are persisted locally; the
  in-memory vector store is hydrated from SQLite on backend startup.
- Exact duplicate uploads are reused by file content hash.
- Schema changes use a small local SQLite upgrade helper, not Alembic yet.
- Qdrant settings are present for future integration; local development currently
  uses SQLite plus the hydrated in-memory vector store.
- `RETRIEVAL_MODE=pageindex` enables an experimental PageIndex-style tree stored
  on long uploaded documents for baseline comparison. `vector` remains default.

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

## Vercel Demo Deploy

The current demo is deployed as two Vercel projects:

- Frontend: `https://citemind-six.vercel.app`
- Backend API: `https://citemind-api.vercel.app`

The plain `citemind.vercel.app` alias is already taken on Vercel. This MVP
backend uses SQLite on Vercel's temporary filesystem, so uploads are suitable
for demos but not durable production storage yet.

## Resume Bullets

- Built a full-stack citation-first research assistant with FastAPI, Next.js, SQLAlchemy, and Tailwind CSS.
- Implemented document upload, chunking, deterministic local retrieval, citation display, query logging, and RAG evaluation.
- Added an intent-aware research agent for summaries, topics, study notes, flashcards, definitions, comparisons, and Q&A.
- Added local heuristic evaluation fallback with optional OpenAI-compatible answer generation and judge-based scoring.
- Containerized the frontend and backend with Docker Compose for local demos.

## Future Improvements

- Persist vector embeddings in Qdrant
- Add migrations with Alembic
- Expand automated tests and CI
