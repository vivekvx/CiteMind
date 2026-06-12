# CiteMind Polish Plan — Session Instructions for Claude Code

## Goal
Take CiteMind from "works but looks AI-generated" to "portfolio piece that sells itself." Score target: 6.5 → 8.5+/10.

## Reference
- Cal.com design system: `/Users/vivek/Downloads/DESIGN-cal.md` (typography hierarchy, spacing rhythm, not their white theme)
- Current stack: Next.js 16 App Router, Tailwind CSS v4, dark zinc/black palette
- Pages: homepage (`/`), contradictions (`/contradictions`), status (`/status`)

## Priority Order

### Phase 1: Demo Mode (CRITICAL — do first)
**Why:** Visitors see "Could not load documents" without backend. Dead end.

Create `frontend/lib/demo-data.ts` with hardcoded fixtures:
- 3 sample medical papers (statin RCT, statin cohort negative, metformin meta-analysis — use existing `tests/fixtures/medical/` as source)
- 8 pre-extracted claims with drug/condition/outcome/direction/study_type/sample_size/grade_score
- 2 contradictions: one HIGH severity DIRECT (statins cardiovascular), one MEDIUM METHODOLOGICAL
- Consensus text for each contradiction group

Toggle: `NEXT_PUBLIC_DEMO_MODE` env var. When true, all API calls return fixture data. When false, normal API behavior.

Files to modify:
- Create `frontend/lib/demo-data.ts` — fixture data
- Modify `frontend/lib/medical-api.ts` — check demo flag, return fixtures
- Modify `frontend/app/page.tsx` — show demo documents when demo mode
- Modify `frontend/app/contradictions/page.tsx` — auto-load demo report

### Phase 2: Homepage Restructure (CRITICAL)
**Why:** Generic RAG Q&A is the landing. MedContradict (the differentiator) is buried.

Option A (recommended): Redesign `/` as a product landing page
- Hero: "Medical papers contradict each other. CiteMind finds where."
- CTA: "Try Demo" button links to `/contradictions` with demo data pre-loaded
- Feature cards: Extract Claims, Grade Evidence, Detect Contradictions, Generate Consensus
- Move RAG Q&A to `/research`

Option B (faster): Just swap — make `/contradictions` the default, move old homepage to `/research`

Files:
- `frontend/app/page.tsx` — new landing or redirect
- `frontend/app/research/page.tsx` — move old RAG UI here
- `frontend/app/layout.tsx` — update nav links
- Move components: `UploadBox`, `QueryPanel`, `AnswerCard`, `EvalCard` stay but are used from `/research`

### Phase 3: UI Polish with Impeccable (`/impeccable polish`)
**Why:** Default Tailwind dark = AI slop fingerprint.

Run in fresh session:
```
/impeccable polish
```

Tell it:
- Register: product (app UI)
- Dark theme — zinc/black palette stays, but needs personality
- Reference: `/Users/vivek/Downloads/DESIGN-cal.md`
- Stack: Next.js 16, Tailwind v4, no motion library yet

Key changes needed:
- **Typography:** Add display font (Inter Tight or Space Grotesk). Negative letter-spacing on headlines (-0.02em to -0.04em). Clear hierarchy: display, title, body, caption.
- **Motion:** Staggered fade-up on cards, smooth page transitions, loading skeleton instead of spinner, hover states on interactive elements. Use `motion` library (framer-motion successor).
- **Spacing:** Vary rhythm between sections (not uniform gap-5 everywhere). Tighter card padding, more breathing room between sections.
- **Brand element:** One unique thing: a subtle accent color, custom icon treatment, or signature component shape.
- **Kill AI tells:** Remove `border-white/[0.08]` pattern, vary card styles, no tiny uppercase tracked eyebrows on every section.

### Phase 4: Visual Proof + README
**Why:** Backend pipeline is invisible. README doesn't sell.

- Record 60s demo GIF: upload papers, analyze, results appear
- README rewrite: hero screenshot, one-line pitch, demo link, THEN technical details
- Add pipeline visualization component showing 9 steps with progress during analysis

### Phase 5: Tests + Empty States
- Integration test: seed DB, extract, detect, assert contradictions
- Empty states: "No documents yet" with icon, error states with retry, loading skeletons
- Fix Vercel auto-deploy: Settings, Git, reconnect, root dir = `frontend`

## Constraints (carry forward from CLAUDE.md)
- Python binary: `backend/.venv/bin/python`
- Module boundaries: `medical/` imports only from `services/` and `models/`
- No auth/multi-tenancy
- Don't rewrite working files outside task scope
- Don't delete LICENSE

## Vercel Deploy
After changes: `cd /Users/vivek/CiteMind/frontend && npx vercel --prod --yes`
Or fix auto-deploy: Vercel dashboard, Settings, Git, reconnect GitHub, root dir `frontend`, framework Next.js
