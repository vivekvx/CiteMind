# CiteMind

CiteMind is a citation-first AI research assistant with retrieval-augmented generation and lightweight RAG evaluation.

## Problem Statement

Researchers need fast answers from documents, but answers are only useful when they can be traced back to supporting evidence. CiteMind focuses on uploads, grounded answers, citations, retrieved chunks, and evaluation scores.

## Features

- Upload research documents
- List uploaded documents
- Ask research questions over uploaded content
- Return answers with citations and retrieved chunks
- Run RAG evaluation with faithfulness, answer relevance, context relevance, and citation coverage scores
- Use OpenAI judge scoring when `OPENAI_API_KEY` exists, with heuristic fallback for local demos

## Architecture

- Frontend: Next.js single-page UI
- Backend: FastAPI API service
- Database: PostgreSQL for documents, query logs, and eval results
- Vector store: Qdrant service target
- Evaluation: OpenAI judge prompts when configured, local heuristics otherwise

## Tech Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Qdrant
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

```bash
cd /Users/vivek/CiteMind
backend/.venv/bin/python -m uvicorn backend.app.main:app --reload
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
DATABASE_URL=
QDRANT_URL=
QDRANT_COLLECTION=citemind_chunks
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## API Endpoints

- `GET /health`
- `POST /documents/upload`
- `GET /documents`
- `POST /query`
- `POST /evals/run`

## Demo Workflow

1. Start the backend.
2. Start the frontend.
3. Upload `sample_docs/sample_ai_report.md`.
4. Ask a research question.
5. Review the answer, citations, and retrieved chunks.
6. Run evaluation and review the score cards.

## Evaluation Metrics

- `faithfulness_score`: whether the answer is supported by retrieved context
- `answer_relevance_score`: whether the answer addresses the user query
- `context_relevance_score`: whether retrieved chunks match the query
- `citation_coverage_score`: whether answer claims include bracket-style citations

## Resume Bullets

- Built a full-stack RAG research assistant with FastAPI, Next.js, PostgreSQL, and Qdrant.
- Implemented document upload, chunking, retrieval, citation display, query logging, and RAG evaluation.
- Added local heuristic evaluation fallback with optional OpenAI judge-based scoring.
- Containerized frontend, backend, database, and vector store with Docker Compose.

## Future Improvements

- Persist vector embeddings in Qdrant
- Add migrations with Alembic
- Support PDF parsing
- Improve citation formatting
- Add automated tests and CI
