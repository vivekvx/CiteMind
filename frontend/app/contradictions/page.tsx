"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ContradictionCard } from "../../components/medical/ContradictionCard";
import { DocumentSelector } from "../../components/medical/DocumentSelector";
import {
  type AnalysisReport,
  type DocumentItem,
  explainContradiction,
  fetchDocuments,
  pollAnalysis,
  startAnalysis,
} from "../../lib/medical-api";

type Phase = "select" | "analyzing" | "done" | "error";

export default function ContradictionsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [phase, setPhase] = useState<Phase>("select");
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDocuments()
      .then(setDocuments)
      .catch(() => setError("Could not load documents."));
  }, []);

  function toggleDoc(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleAnalyze() {
    if (selected.size < 2) return;
    setPhase("analyzing");
    setError("");
    setReport(null);
    try {
      const { job_id } = await startAnalysis([...selected]);
      const finalReport = await pollAnalysis(job_id);
      setReport(finalReport);
      setPhase("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
      setPhase("error");
    }
  }

  function handleReset() {
    setPhase("select");
    setReport(null);
    setError("");
  }

  const handleExplain = useCallback(async (id: number) => {
    return explainContradiction(id);
  }, []);

  const highCount =
    report?.contradictions.filter(
      (c) => c.severity.toUpperCase() === "HIGH",
    ).length ?? 0;
  const medCount =
    report?.contradictions.filter(
      (c) => c.severity.toUpperCase() === "MEDIUM",
    ).length ?? 0;
  const lowCount =
    report?.contradictions.filter(
      (c) => c.severity.toUpperCase() === "LOW",
    ).length ?? 0;

  return (
    <main className="min-h-screen px-4 py-6 text-zinc-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Header */}
        <header className="rounded-lg border border-white/10 bg-white/[0.045] px-5 py-5 shadow-2xl shadow-black/30 backdrop-blur md:px-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">
                MedContradict
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">
                Contradiction Analysis
              </h1>
            </div>
            <div className="flex items-center gap-2">
              <Link
                className="rounded-md border border-white/15 bg-white/[0.06] px-3 py-2 text-xs font-medium text-zinc-200 hover:border-white/30 hover:bg-white/[0.1]"
                href="/"
              >
                Back to CiteMind
              </Link>
            </div>
          </div>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-zinc-400">
            Select two or more uploaded medical papers to detect contradictory
            findings across studies. Claims are extracted, graded by evidence
            level, and compared for conflicting conclusions.
          </p>
        </header>

        {error ? (
          <div className="rounded-md border border-red-500/20 bg-red-500/[0.06] px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        ) : null}

        {/* Selection phase */}
        {phase === "select" || phase === "error" ? (
          <section className="rounded-lg border border-white/10 bg-zinc-950/70 p-5 shadow-2xl shadow-black/30 backdrop-blur">
            <h2 className="text-sm font-semibold text-white">
              Select Documents
            </h2>
            <p className="mt-1 text-xs text-zinc-500">
              Choose at least 2 papers to compare
            </p>
            <div className="mt-4">
              <DocumentSelector
                documents={documents}
                selected={selected}
                onToggle={toggleDoc}
              />
            </div>
            <div className="mt-5 flex items-center gap-3">
              <button
                type="button"
                disabled={selected.size < 2}
                onClick={handleAnalyze}
                className="rounded-md bg-white px-5 py-2.5 text-sm font-semibold text-black shadow-lg shadow-black/30 hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500"
              >
                Analyze {selected.size > 0 ? `(${selected.size} docs)` : ""}
              </button>
              <span className="text-xs text-zinc-600">
                {selected.size < 2
                  ? `Select ${2 - selected.size} more`
                  : "Ready to analyze"}
              </span>
            </div>
          </section>
        ) : null}

        {/* Analyzing phase */}
        {phase === "analyzing" ? (
          <section className="rounded-lg border border-white/10 bg-zinc-950/70 p-8 text-center shadow-2xl shadow-black/30 backdrop-blur">
            <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-zinc-700 border-t-white" />
            <p className="text-sm font-medium text-zinc-200">
              Analyzing {selected.size} documents...
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              Extracting claims, detecting contradictions, generating
              explanations
            </p>
          </section>
        ) : null}

        {/* Results phase */}
        {phase === "done" && report ? (
          <>
            <section className="rounded-lg border border-white/10 bg-white/[0.045] p-5 shadow-2xl shadow-black/30 backdrop-blur">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-white">
                    Analysis Complete
                  </h2>
                  <p className="mt-0.5 text-xs text-zinc-500">
                    Job {report.job_id.slice(0, 8)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleReset}
                  className="rounded-md border border-white/15 bg-white/[0.06] px-3 py-2 text-xs font-medium text-zinc-200 hover:border-white/30 hover:bg-white/[0.1]"
                >
                  New Analysis
                </button>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatCard
                  label="Documents"
                  value={report.document_ids.length}
                />
                <StatCard label="Claims Found" value={report.total_claims} />
                <StatCard
                  label="Contradictions"
                  value={report.total_contradictions}
                  highlight={report.total_contradictions > 0}
                />
                <StatCard label="High Severity" value={highCount} alert />
              </div>
            </section>

            {report.total_contradictions > 0 ? (
              <div className="flex flex-wrap gap-2">
                {highCount > 0 ? (
                  <span className="rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1 text-xs font-medium text-red-400">
                    {highCount} High
                  </span>
                ) : null}
                {medCount > 0 ? (
                  <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-400">
                    {medCount} Medium
                  </span>
                ) : null}
                {lowCount > 0 ? (
                  <span className="rounded-full border border-zinc-500/30 bg-zinc-500/10 px-3 py-1 text-xs font-medium text-zinc-400">
                    {lowCount} Low
                  </span>
                ) : null}
              </div>
            ) : null}

            {report.total_contradictions === 0 ? (
              <section className="rounded-lg border border-dashed border-white/[0.12] bg-white/[0.02] px-5 py-10 text-center">
                <p className="text-sm text-zinc-400">
                  No contradictions detected between the selected documents.
                </p>
                <p className="mt-1 text-xs text-zinc-600">
                  The papers may agree on their findings, or claims could not be
                  matched across documents.
                </p>
              </section>
            ) : (
              <div className="space-y-4">
                {report.contradictions.map((c, i) => (
                  <ContradictionCard
                    key={c.id}
                    contradiction={c}
                    index={i}
                    onExplain={handleExplain}
                  />
                ))}
              </div>
            )}
          </>
        ) : null}
      </div>
    </main>
  );
}

function StatCard({
  label,
  value,
  highlight,
  alert,
}: {
  label: string;
  value: number;
  highlight?: boolean;
  alert?: boolean;
}) {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
      <p className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
        {label}
      </p>
      <p
        className={`mt-1 text-2xl font-semibold tabular-nums ${
          alert && value > 0
            ? "text-red-400"
            : highlight
              ? "text-amber-300"
              : "text-white"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
