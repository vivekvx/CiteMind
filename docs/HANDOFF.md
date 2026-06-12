# CiteMind — Session Handoff (2026-06-12)

## TL;DR
Frontend is polished and live. Backend is **broken in production** and needs the Option 2 rewrite (locked plan in `docs/BACKEND-FIX-PLAN.md`). Start the rewrite in a FRESH session — this one's context is huge/expensive.

## What works right now
- **Demo:** https://citemind-six.vercel.app — `/contradictions` runs on built-in fixture papers (frontend-only, no backend needed). Fully functional for showing the pipeline.
- Landing page, `/research` RAG UI, `/status`, nav, typography (Inter Tight + Inter), motion, skeletons, empty states.
- Vercel **frontend** auto-deploy: reconnected + verified (push to `main` -> auto build).

## What's broken
- **Backend (`citemind-api.vercel.app`) is down** — 500 on all routes including `/documents/upload`.
- Root cause: torch + sentence-transformers (BGE-M3 embeddings) ~1GB, exceeds Vercel's 250MB lambda limit -> function import fails.
- Secondary: `BackgroundTasks` + ephemeral SQLite break the analyze-job polling on serverless.
- Net effect: uploading and analyzing real papers does not work in production. Demo masks this.

## The fix (DECISION LOCKED: Option 2)
Full step-by-step in **`docs/BACKEND-FIX-PLAN.md`**. Summary:
1. `embeddings.py` -> OpenAI `text-embedding-3-small` via httpx (drop torch).
2. `vector_store.py` -> Qdrant dim 1024 -> 1536, recreate collection on mismatch.
3. `requirements.txt` -> remove `sentence-transformers` (bundle fits 250MB).
4. `routes/medical.py` -> make `/medical/analyze` synchronous (drop BackgroundTasks).
5. `frontend/lib/medical-api.ts` -> poll resolves on first hit (job already `done`).
6. Vercel env (user sets): `OPENAI_API_KEY`, `DATABASE_URL` (Neon/Supabase Postgres), `LLM_PROVIDER=openai`.
7. CORS in `main.py` -> allow `https://citemind-six.vercel.app`.
8. Redeploy `citemind-api`, verify upload + analyze end to end.

### Timeout watch
Vercel hobby=10s / pro=60s. Multi-LLM analyze may time out. Mitigation: cap explained contradictions, or return report without inline explanations (use existing `/medical/explain/{id}` on demand).

## Done this session (all merged to main)
- Fixed 6 backend bugs: async analyze, N+1 LLM calls, OpenRouter hardcoded model, confidence parsing, outcome grouping, schema nullability.
- Demo mode (`frontend/lib/demo-data.ts`).
- Homepage restructure: MedContradict landing at `/`, RAG moved to `/research`.
- UI polish: fonts, motion system, skeletons, `prefers-reduced-motion`.
- README rewrite + 4 screenshots (`docs/assets/`).
- Integration test (`tests/medical/test_pipeline_integration.py`), 21 tests passing.
- DocumentSelector empty state.
- Vercel frontend Git reconnect.

## Key facts for next session
- Branch: `feature/medcontradict` (merge to `main` via `gh api repos/vivekvx/CiteMind/merges`, worktree can't checkout main).
- Python: `backend/.venv/bin/python`. Tests: `PYTHONPATH=. backend/.venv/bin/python -m pytest tests/`.
- Backend deploys from repo ROOT (`api/index.py` -> `backend.app.main:app`), project `citemind-api` (prj_Mb96lM9jOR1jKIYgD1cyDzUErx4Q). Frontend project `citemind` (prj_vGT79dAEOOfYUvhlQwmlUlIP6iue). Team `team_rQJFlMZQqwte7MTrYYds6XmO`.
- Module boundaries: `medical/` imports only from `services/`+`models/`, calls `llm_client.py` only. Don't delete LICENSE.

## Cost note
This session ran very long (>$500 cumulative). Do the rewrite in a fresh session.
