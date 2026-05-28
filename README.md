# CiteMind

CiteMind is a citation-first AI research assistant for document Q&A, research summaries, and lightweight RAG evaluation.

## Problem Statement

Researchers need fast answers from documents, but answers are only useful when they can be traced back to supporting evidence. CiteMind focuses on uploads, grounded answers, citations, retrieved chunks, and evaluation scores.

## Current Phase

CiteMind is currently in a local MVP/demo phase. The app supports the full loop of uploading a document, asking questions over the selected document, receiving cited answers, and running evaluation scores from the UI.

The backend defaults to SQLite and an in-memory vector store with deterministic local embeddings, so the demo can run without external services. OpenAI is optional: when `OPENAI_API_KEY` is configured, CiteMind uses OpenAI for answer synthesis and judge-style evaluation; otherwise it falls back to local extractive answers and heuristic scoring.

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
- Retrieval: In-memory vector store with deterministic hash embeddings in the current MVP phase.
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
DATABASE_URL=sqlite:///./citemind.db
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=citemind_chunks
NEXT_PUBLIC_API_URL=http://localhost:8001
```

If you run the backend with the default uvicorn port from the command above, set `NEXT_PUBLIC_API_URL=http://localhost:8000` before starting the frontend.

## API Endpoints

- `GET /health`
- `POST /documents/upload`
- `GET /documents`
- `POST /query`
- `POST /evals/run`

## Demo Workflow

1. Start the backend API.
2. Start the frontend.
3. Upload `sample_docs/sample_ai_report.md`.
4. Ask a research question, summary request, topic request, study-note prompt, or flashcard prompt.
5. Review the answer, citations, and retrieved chunks.
6. Run evaluation and review the score cards.

## Evaluation Metrics

- `faithfulness_score`: whether the answer is supported by retrieved context
- `answer_relevance_score`: whether the answer addresses the user query
- `context_relevance_score`: whether retrieved chunks match the query
- `citation_coverage_score`: whether answer claims include bracket-style citations

## Resume Bullets

- Built a full-stack citation-first research assistant with FastAPI, Next.js, SQLAlchemy, and Tailwind CSS.
- Implemented document upload, chunking, deterministic local retrieval, citation display, query logging, and RAG evaluation.
- Added an intent-aware research agent for summaries, topics, study notes, flashcards, definitions, comparisons, and Q&A.
- Added local heuristic evaluation fallback with optional OpenAI answer generation and judge-based scoring.
- Containerized frontend, backend, database, and vector store with Docker Compose.

## Future Improvements

- Persist vector embeddings in Qdrant
- Add migrations with Alembic
- Support PDF parsing
- Improve citation formatting
- Add automated tests and CI
