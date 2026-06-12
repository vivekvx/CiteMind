import { DEMO_DOCUMENTS, DEMO_MODE, DEMO_REPORT } from "./demo-data";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export type ClaimOut = {
  id: number;
  document_id: number;
  chunk_index: number;
  drug: string;
  condition: string;
  outcome: string;
  direction: string;
  population: string | null;
  study_type: string;
  sample_size: number | null;
  effect_size: string | null;
  confidence: number;
  raw_text: string;
  grade_score: number;
  evidence_label: string;
};

export type ContradictionOut = {
  id: number;
  claim_a: ClaimOut | null;
  claim_b: ClaimOut | null;
  contradiction_type: string;
  severity: string;
  explanation: string | null;
  consensus: string | null;
};

export type AnalysisReport = {
  job_id: string;
  document_ids: number[];
  total_claims: number;
  total_contradictions: number;
  contradictions: ContradictionOut[];
};

export type DocumentItem = {
  id: number;
  title: string;
  source_url?: string | null;
  abstract?: string | null;
  created_at: string;
  updated_at: string;
};

export async function fetchDocuments(): Promise<DocumentItem[]> {
  if (DEMO_MODE) return DEMO_DOCUMENTS;
  const res = await fetch(`${API_URL}/documents`);
  if (!res.ok) throw new Error("Failed to load documents");
  return res.json();
}

export async function startAnalysis(
  documentIds: number[],
): Promise<{ job_id: string; status: string }> {
  if (DEMO_MODE) return { job_id: DEMO_REPORT.job_id, status: "done" };
  const res = await fetch(`${API_URL}/medical/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_ids: documentIds }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(err.detail || "Analysis failed");
  }
  return res.json();
}

export async function pollAnalysis(
  jobId: string,
  pollIntervalMs = 2000,
  maxAttempts = 300,
): Promise<AnalysisReport> {
  if (DEMO_MODE) {
    await new Promise((r) => setTimeout(r, 1500));
    return DEMO_REPORT;
  }
  for (let i = 0; i < maxAttempts; i++) {
    const result = await getAnalysis(jobId);
    if (result.status === "done" && result.report) return result.report;
    if (result.status === "failed") {
      throw new Error(result.error || "Analysis failed");
    }
    await new Promise((r) => setTimeout(r, pollIntervalMs));
  }
  throw new Error("Analysis timed out");
}

export async function getAnalysis(jobId: string): Promise<{
  status: "done" | "running" | "failed";
  report?: AnalysisReport;
  error?: string;
}> {
  const res = await fetch(`${API_URL}/medical/analyze/${jobId}`);
  if (res.status === 202) return { status: "running" };
  if (res.status === 500) {
    const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
    return { status: "failed", error: err.detail };
  }
  if (!res.ok) throw new Error("Failed to fetch analysis");
  const report: AnalysisReport = await res.json();
  return { status: "done", report };
}

export async function explainContradiction(
  contradictionId: number,
): Promise<string> {
  if (DEMO_MODE) {
    const c = DEMO_REPORT.contradictions.find((x) => x.id === contradictionId);
    return c?.explanation ?? "No explanation available in demo mode.";
  }
  const res = await fetch(`${API_URL}/medical/explain/${contradictionId}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to generate explanation");
  const data = await res.json();
  return data.explanation;
}
