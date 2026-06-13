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

## DECISION LOCKED: Option 2 (stay on Vercel, rewrite)

User chose Option 2 on 2026-06-12. Execute these exact steps in a FRESH session.

### Step-by-step

1. **`backend/app/services/embeddings.py`** — replace BGE-M3/sentence-transformers with OpenAI embeddings API.
   - Call `text-embedding-3-small` (1536-dim) via `httpx` POST to `https://api.openai.com/v1/embeddings` using `settings.openai_api_key`. Keep the `embed_text` / `embed_chunks` signatures unchanged so callers don't break.
   - Batch chunks in one request; return `data[i].embedding` lists.
   - No torch, no sentence-transformers imported anywhere.

2. **`backend/app/services/vector_store.py`** — change the Qdrant collection vector size from 1024 to **1536** (text-embedding-3-small). If an old `citemind_chunks` collection exists with dim 1024, it must be recreated. Add a one-time guard that recreates the collection if the dim mismatches.

3. **`requirements.txt`** — remove `sentence-transformers>=2.7.0`. Keep `httpx`, `qdrant-client`, `psycopg2-binary`. This drops torch and gets the bundle under Vercel's 250MB limit.

4. **`backend/app/routes/medical.py`** — make `POST /medical/analyze` **synchronous**. Remove `BackgroundTasks` and `_run_analysis_job`; run detect -> explain -> consensus inline and return the full `AnalysisReport` directly (still persist the `AnalysisJob` row as `done` so `GET /medical/analyze/{job_id}` keeps working). Keep total LLM calls bounded; if it risks the function timeout, cap explanations to top-N contradictions.

5. **`frontend/lib/medical-api.ts`** — `startAnalysis` can now return the report directly. Either: keep `pollAnalysis` (it will resolve on first poll since job is already `done`), or short-circuit when the POST response already contains the report. Simplest: have `startAnalysis` return `{job_id}` and let one poll fetch the stored `done` job.

6. **Vercel env vars (user provides):**
   - `OPENAI_API_KEY` on the `citemind-api` project (embeddings + LLM).
   - `DATABASE_URL` = a managed Postgres URL (Neon/Supabase free tier) on `citemind-api`. Required so documents/claims/contradictions/jobs persist across lambda invocations.
   - Confirm `LLM_PROVIDER=openai` (or `auto` with the key set).

7. **CORS** in `backend/app/main.py` — ensure `allow_origins` includes `https://citemind-six.vercel.app`.

8. **Redeploy `citemind-api`** (root project, `api/index.py`). Then verify end to end:
   - `POST /documents/upload` with a real PDF -> 200
   - `/contradictions` -> select 2 -> Analyze -> report returns, no 404/500.

### Timeout watch
Vercel hobby = 10s, pro = 60s function limit. Analysis makes multiple LLM calls. If it times out, either upgrade to pro, cap explained contradictions, or move explanation to a separate on-demand `/medical/explain/{id}` call (already exists) and return the report without inline explanations.

## Constraints (from CLAUDE.md)
- Python binary: `backend/.venv/bin/python`
- `medical/` imports only from `services/` and `models/`
- `medical/` calls `llm_client.py`, never OpenAI/Ollama SDK directly
- Don't delete LICENSE

## Note on cost
The session that diagnosed this ran very long. Start the fix in a FRESH session; this conversation's context is large and expensive to carry.
