# Backend Production Fix — Instructions for Next Claude Code Session

## The Problem (confirmed 2026-06-12)

Real paper upload + contradiction analysis **does not work in production**. Demo mode (`/contradictions` with built-in fixture papers) works because it is pure frontend. Uploading real PDFs and clicking Analyze fails.

### Evidence
| Check | Result |
|-------|--------|
| `GET /documents` on `citemind-api.vercel.app` | 200 OK |
| `POST /medical/analyze` (before backend redeploy) | 404 — backend was stale (last deploy May 31, pre-MedContradict) |
| `POST /medical/analyze` (after redeploy) | 500 — `could not import "api/index"` |

### Root cause: backend cannot run on Vercel serverless

1. **Lambda size limit.** Backend bundles `sentence-transformers` + `torch` (BGE-M3 embeddings) ~1GB+. Vercel's limit is 250MB unzipped, so the function fails to import and returns 500. `/documents` works only because it does not trigger the heavy import path in that invocation.

2. **Stateful job pattern incompatible with serverless.** `POST /medical/analyze` creates an `AnalysisJob` row (status `running`), returns a `job_id`, and runs `_run_analysis_job` via FastAPI `BackgroundTasks`. The frontend then polls `GET /medical/analyze/{job_id}`. On serverless: (a) SQLite is ephemeral per-invocation, so the job is invisible to the polling lambda; (b) the lambda freezes after returning the response, so the background task never completes. Both break polling.

## Pick one option

### Option 1 — Host backend on a persistent server (RECOMMENDED)
Move `citemind-api` off Vercel to Railway / Render / Fly.io.
- Long-lived process fits torch + sentence-transformers, runs BackgroundTasks to completion.
- Add managed Postgres; set `DATABASE_URL` to it. `Base.metadata.create_all` already creates tables on startup.
- Point frontend `NEXT_PUBLIC_API_URL` (Vercel env) at the new backend URL; update CORS `allow_origins` in `backend/app/main.py` to include `https://citemind-six.vercel.app`.
- Verify: upload 2 real papers via `/research`, run analysis on `/contradictions`, confirm job completes.
- ~1-2 hrs. Correct architecture for this workload.

### Option 2 — Make it Vercel-compatible
Strip the heavy deps and the async pattern.
- Replace BGE-M3 local embeddings with an API (OpenAI `text-embedding-3-small`) in `backend/app/services/embeddings.py` to remove torch/sentence-transformers from the bundle.
- Make `POST /medical/analyze` **synchronous** (no BackgroundTasks): run detect, explain, consensus inline, return the report directly. Drop the polling path or keep `getAnalysis` returning the stored result.
- Requires persistent Postgres anyway (`DATABASE_URL`) for documents/claims/contradictions across invocations.
- Watch the 10s (hobby) / 60s (pro) function timeout: multiple LLM calls may exceed it. May still need a queue.
- Bigger code change; serverless timeout risk remains.

### Option 3 — Honest demo-only (zero backend spend)
Keep production as a frontend demo.
- README note: "The live demo runs on built-in sample papers. To analyze your own papers, self-host the backend (see Quick Start)."
- Add a small banner on `/contradictions` when `DEMO_MODE` is active: "Demo data, self-host to analyze your own papers."
- Cheapest. Accurate. Loses the "works on real papers" credibility the founder review asked for.

## Recommendation
Option 1 if you want it to genuinely work (best portfolio signal: "deployed a real ML backend, not just a serverless toy"). Option 3 if you want to stop spending now and be honest about scope. Avoid Option 2 unless you specifically want to keep everything on Vercel.

## Constraints (from CLAUDE.md)
- Python binary: `backend/.venv/bin/python`
- `medical/` imports only from `services/` and `models/`
- `medical/` calls `llm_client.py`, never OpenAI/Ollama SDK directly
- Don't delete LICENSE

## Note on cost
The session that diagnosed this ran very long. Start the fix in a FRESH session; this conversation's context is large and expensive to carry.
