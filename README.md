# CiteMind

CiteMind is a citation-first AI research assistant for document Q&A, summaries, and lightweight RAG evaluation. It combines a Next.js interface with a FastAPI retrieval backend, persisted document chunks, optional OpenAI-compatible LLM synthesis, and visible answer-quality metrics.

## Live Demo

- Frontend: https://citemind-six.vercel.app
- Backend API: https://citemind-api.vercel.app
- Health check: https://citemind-six.vercel.app/api/health

## Screenshots

![CiteMind upload, document selection, and cited answer workflow](docs/images/citemind-workflow.png)

![CiteMind retrieved chunks and evaluation score cards](docs/images/citemind-evaluation.png)

## What It Does

- Upload PDF, EPUB, Markdown, or text documents.
- Ask questions against the selected document.
- Generate cited answers for summaries, topics, study notes, flashcards, comparisons, definitions, and Q&A.
- Show retrieved chunks so answers can be audited.
- Run evaluation for faithfulness, answer relevance, context relevance, and citation coverage.
- Reset the local demo to the bundled `sample_docs/sample_ai_report.md`.

## Architecture

```mermaid
flowchart LR
    A["Next.js UI"] --> B["API route rewrite / NEXT_PUBLIC_API_URL"]
    B --> C["FastAPI backend"]
    C --> D["Document loader"]
    D --> E["Chunk store"]
    E --> F["SQLite or Postgres"]
    E --> G["In-memory vector index"]
    C --> H["Intent router"]
    H --> I["Retriever"]
    I --> G
    I --> E
    H --> J["Answer generator"]
    J --> K["OpenAI-compatible LLM"]
    J --> L["Local fallback"]
    H --> M["Evaluator"]
    M --> K
    M --> L
```

### Components

- Frontend: Next.js, React, TypeScript, Tailwind CSS.
- Backend: FastAPI, SQLAlchemy, Pydantic.
- Retrieval: persisted chunks, deterministic embeddings, hydrated in-memory vector index.
- Storage: SQLite locally, Postgres-compatible `DATABASE_URL` for hosted persistence.
- LLM: OpenAI-compatible chat providers through `LLM_*` or `OPENAI_*`.
- Deployment: Vercel frontend and Vercel Python backend.

## Quick Start

Install backend dependencies:

```bash
cd CiteMind/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

Install frontend dependencies:

```bash
cd ../frontend
npm install
```

Run the app:

```bash
cd ..
./dev.sh
```

Local URLs:

- Frontend: `http://localhost:3001`
- Backend docs: `http://localhost:8001/docs`

Docker:

```bash
docker compose up --build
```

## Configuration

Copy `.env.example` to `.env` and configure only what you need.

```bash
DATABASE_URL=sqlite:///./citemind.db

LLM_API_KEY=
LLM_BASE_URL=
LLM_CHAT_MODEL=

OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

NEXT_PUBLIC_API_URL=http://localhost:8001
BACKEND_API_URL=

MAX_UPLOAD_BYTES=10000000
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=20
```

For local frontend runs, create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
```

For Vercel frontend deployments:

```bash
NEXT_PUBLIC_API_URL=/api
BACKEND_API_URL=<deployed-backend-url>
```

For hosted persistence:

```bash
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
```

Do not commit real `.env` files or API keys.

## LLM Providers

`LLM_*` settings take precedence over `OPENAI_*`, so the backend can use OpenRouter, DeepSeek, OpenAI, or another OpenAI-compatible provider without code changes.

OpenRouter:

```bash
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=<your-openrouter-key>
LLM_CHAT_MODEL=openrouter/free
```

DeepSeek:

```bash
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=<your-deepseek-key>
LLM_CHAT_MODEL=deepseek-chat
```

Check provider status:

```bash
curl http://localhost:8001/health/llm
```

## API

- `GET /health`
- `GET /health/llm`
- `POST /documents/upload`
- `POST /documents/demo/reset`
- `GET /documents`
- `DELETE /documents/{document_id}`
- `POST /query`
- `POST /evals/run`

## Verification

Backend:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/citemind-pycache backend/.venv/bin/python -m compileall api backend/__init__.py backend/app
backend/.venv/bin/python -m unittest backend.app.tests.test_regressions
backend/.venv/bin/python -c "from backend.app.main import app; print(app.title)"
```

Frontend:

```bash
cd frontend
npm run build
```

Formatting:

```bash
cd ..
git diff --check
```

## Deployment

Current Vercel projects:

- Frontend: `https://citemind-six.vercel.app`
- Backend API: `https://citemind-api.vercel.app`

Recommended backend environment:

```bash
DATABASE_URL=<hosted-postgres-url>
LLM_API_KEY=<openrouter-or-compatible-provider-key>
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_CHAT_MODEL=openrouter/free
MAX_UPLOAD_BYTES=10000000
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=20
```

If hosted Postgres is not configured, Vercel uploads are demo-only because serverless filesystem storage is temporary.

## Project Status

Implemented:

- Document ingestion, chunk persistence, deduplication, and deletion.
- Document-scoped retrieval with deterministic local embeddings.
- Optional LLM synthesis with local fallback behavior.
- Inline citations, retrieved chunk display, and evaluation cards.
- Docker Compose and Vercel deployment support.
- Basic rate limiting for costly public routes.

Next improvements:

- Move public demo persistence to hosted Postgres.
- Add Alembic migrations.
- Add account-level auth before broad public release.
- Compare Qdrant and PageIndex retrieval against the current baseline.
- Add CI for backend tests and frontend builds.
