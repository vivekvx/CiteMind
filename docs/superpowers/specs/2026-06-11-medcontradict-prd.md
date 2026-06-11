# MedContradict — Product Requirements Document

**Version:** 1.0  
**Date:** 2026-06-11  
**Status:** Approved  

---

## 1. Problem Statement

Doctors, researchers, and systematic reviewers spend 4–8 hours per week manually cross-referencing medical literature to determine whether studies agree or contradict each other on a given treatment. Existing tools (PubMed, UpToDate, ChatGPT, NotebookLM) either require manual reading or provide summaries without surfacing disagreements. No tool automatically detects when two papers reach opposite conclusions on the same drug/condition and explains why.

---

## 2. Product Vision

CiteMind evolves from a "chat with PDF" tool into a **medical literature intelligence platform** that finds what humans miss: contradictions, conflicting evidence, and evolving consensus across papers.

**North Star Demo:**  
> "Upload 3 papers on metformin + heart failure. Show me where they disagree, which evidence is strongest, and why results differ."

---

## 3. Target Users

| User | Pain Point | Value Delivered |
|------|-----------|-----------------|
| Clinical researcher | Manual systematic reviews take weeks | Contradiction detection in minutes |
| Hospital pharmacist | Conflicting drug guidelines across organizations | Side-by-side claim comparison with evidence grades |
| Medical student | Can't assess evidence quality across papers | Automatic GRADE scoring |
| Pharma R&D | Safety signal detection across literature | Cross-document claim extraction + conflict flagging |

---

## 4. User Stories

### Core (MVP)
- **US-01:** As a researcher, I upload 2+ papers on the same topic so that the system extracts structured medical claims from each.
- **US-02:** As a researcher, I trigger a contradiction analysis across selected papers so that I see which claims conflict.
- **US-03:** As a researcher, I view a contradiction report showing opposing claims side-by-side with evidence strength scores.
- **US-04:** As a researcher, I see an LLM-generated explanation of WHY two papers reached different conclusions (population, dosage, study design).
- **US-05:** As a researcher, I see a consensus statement summarizing current best evidence on the topic.

### Secondary (Post-MVP)
- **US-06:** As a researcher, I search papers by drug/condition without uploading (PubMed integration).
- **US-07:** As a researcher, I export the contradiction report as PDF.
- **US-08:** As a researcher, I see a timeline of how consensus evolved year-by-year.

---

## 5. Success Metrics (MVP)

| Metric | Target |
|--------|--------|
| Claim extraction accuracy | ≥80% of real claims correctly extracted from a test paper |
| Contradiction detection precision | ≥75% of flagged contradictions are real contradictions |
| End-to-end latency (3 papers) | <60 seconds from upload to report |
| Demo scenario working | Upload metformin + HF papers → see correct contradictions |

---

## 6. Out of Scope (MVP)

- PubMed auto-fetch
- User authentication / multi-tenancy
- PDF export of reports
- Real-time collaboration
- Retraction database integration
- Mobile app

---

## 7. Constraints

- **Zero API budget for development:** Must run fully on local Ollama (llama3.2). OpenAI/OpenRouter supported as optional upgrade when budget available.
- **Single developer:** Scope must be achievable in ~5 weeks.
- **Existing codebase:** Must extend CiteMind without rewriting working backend/frontend.
- **Deployment:** Local Docker for development. Railway/Vercel for production when ready.

---

## 8. Feature Breakdown

### F1: Claim Extraction
- Triggered automatically on document upload
- LLM extracts structured claims: {drug, condition, outcome, direction, population, study_type, sample_size, effect_size}
- Claims stored in DB linked to source document + chunk (traceable)
- Works with Ollama local model; optional OpenAI for higher accuracy

### F2: Contradiction Detection
- User selects 2+ documents
- System groups claims by {drug + condition + outcome} (semantic matching)
- Flags pairs where `direction` differs (positive vs negative/neutral)
- Classifies type: DIRECT, PARTIAL, METHODOLOGICAL, TEMPORAL

### F3: Evidence Grading
- GRADE framework: meta-analysis > RCT > cohort > case-control > case series
- Adjusted for sample size
- Displayed as visual strength bar in UI

### F4: Disagreement Explanation
- LLM prompt given both claims + source chunks
- Outputs structured explanation: population differences, dosage, endpoints, follow-up, design
- Cached per contradiction pair

### F5: Contradiction Report UI
- New page `/contradictions`
- Document selector (multi-select from uploaded docs)
- "Analyze" button triggers pipeline
- Report shows: claim groups, contradictions, evidence bars, explanations, consensus

---

## 9. Rollout Plan

| Week | Deliverable |
|------|-------------|
| 1 | Fix foundations: BGE-M3 embeddings, Qdrant, Docling, Ollama in Docker |
| 2 | Claim extraction pipeline + DB schema |
| 3 | Contradiction detection + evidence grader |
| 4 | Explainer + contradiction report UI |
| 5 | Polish, eval with real papers, RAGAS metrics |
