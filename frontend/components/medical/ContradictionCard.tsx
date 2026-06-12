"use client";

import { useState } from "react";
import type { ClaimOut, ContradictionOut } from "../../lib/medical-api";
import { EvidenceBar } from "./EvidenceBar";

type ContradictionCardProps = {
  contradiction: ContradictionOut;
  index: number;
  onExplain?: (id: number) => Promise<string>;
};

const SEVERITY_STYLES: Record<string, string> = {
  HIGH: "border-red-500/40 bg-red-500/10 text-red-400",
  MEDIUM: "border-amber-500/40 bg-amber-500/10 text-amber-400",
  LOW: "border-zinc-500/40 bg-zinc-500/10 text-zinc-400",
};

const TYPE_LABELS: Record<string, string> = {
  DIRECT: "Direct Contradiction",
  METHODOLOGICAL: "Methodological",
  PARTIAL: "Partial",
  TEMPORAL: "Temporal",
};

const DIRECTION_ICONS: Record<string, { symbol: string; color: string }> = {
  positive: { symbol: "↑", color: "text-emerald-400" },
  negative: { symbol: "↓", color: "text-red-400" },
  neutral: { symbol: "↔", color: "text-zinc-400" },
  unclear: { symbol: "?", color: "text-zinc-500" },
};

function ClaimSide({ claim, side }: { claim: ClaimOut; side: "A" | "B" }) {
  const dir = DIRECTION_ICONS[claim.direction] || DIRECTION_ICONS.unclear;
  return (
    <div className="flex-1 rounded-lg border border-white/[0.08] bg-white/[0.025] p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="rounded-full bg-white/[0.06] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
          Claim {side}
        </span>
        <span className={`text-lg font-semibold ${dir.color}`}>
          {dir.symbol}
        </span>
      </div>

      <p className="text-sm font-semibold text-zinc-100">
        {claim.drug}
        <span className="mx-1.5 text-zinc-600">&rarr;</span>
        {claim.condition}
      </p>
      <p className="mt-1 text-xs text-zinc-400">{claim.outcome}</p>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-white/[0.06] px-2 py-0.5 text-[11px] font-medium text-zinc-400">
          {claim.study_type.replace("_", " ")}
        </span>
        {claim.sample_size ? (
          <span className="text-[11px] text-zinc-500">
            n={claim.sample_size.toLocaleString()}
          </span>
        ) : null}
        {claim.effect_size ? (
          <span className="text-[11px] text-zinc-500">{claim.effect_size}</span>
        ) : null}
      </div>

      <div className="mt-3">
        <EvidenceBar score={claim.grade_score} label={claim.evidence_label} />
      </div>

      <p className="mt-3 border-t border-white/[0.06] pt-3 text-xs leading-relaxed text-zinc-500">
        &ldquo;
        {claim.raw_text.length > 200
          ? claim.raw_text.slice(0, 200) + "…"
          : claim.raw_text}
        &rdquo;
      </p>
    </div>
  );
}

export function ContradictionCard({
  contradiction,
  index,
  onExplain,
}: ContradictionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [localExplanation, setLocalExplanation] = useState(
    contradiction.explanation,
  );

  const severity = contradiction.severity.toUpperCase();
  const sevStyle = SEVERITY_STYLES[severity] || SEVERITY_STYLES.LOW;
  const typeLabel =
    TYPE_LABELS[contradiction.contradiction_type] ||
    contradiction.contradiction_type;

  async function handleExplain() {
    if (localExplanation || !onExplain) return;
    setExplaining(true);
    try {
      const text = await onExplain(contradiction.id);
      setLocalExplanation(text);
    } finally {
      setExplaining(false);
    }
  }

  return (
    <div className="card-hover rounded-xl border border-white/[0.08] bg-zinc-950/60 shadow-2xl shadow-black/20 backdrop-blur">
      <div className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-3.5">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/[0.06] text-xs font-semibold text-zinc-400">
          {index + 1}
        </span>
        <span
          className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${sevStyle}`}
        >
          {severity}
        </span>
        <span className="rounded-full bg-white/[0.06] px-2.5 py-0.5 text-[11px] font-medium text-zinc-400">
          {typeLabel}
        </span>
      </div>

      <div className="flex flex-col gap-3 p-5 md:flex-row">
        {contradiction.claim_a ? (
          <ClaimSide claim={contradiction.claim_a} side="A" />
        ) : (
          <div className="flex-1 rounded-lg border border-white/[0.08] bg-white/[0.025] p-4 text-xs text-zinc-500">
            Claim A unavailable
          </div>
        )}
        <div className="flex items-center justify-center md:px-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-full border border-white/[0.1] bg-white/[0.04] text-xs font-bold text-zinc-500">
            VS
          </div>
        </div>
        {contradiction.claim_b ? (
          <ClaimSide claim={contradiction.claim_b} side="B" />
        ) : (
          <div className="flex-1 rounded-lg border border-white/[0.08] bg-white/[0.025] p-4 text-xs text-zinc-500">
            Claim B unavailable
          </div>
        )}
      </div>

      <div className="border-t border-white/[0.06]">
        <button
          type="button"
          onClick={() => {
            setExpanded(!expanded);
            if (!expanded && !localExplanation) handleExplain();
          }}
          className="flex w-full items-center justify-between px-5 py-3 text-left text-sm font-medium text-zinc-300 hover:text-white"
        >
          <span>Analysis &amp; Explanation</span>
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            className={`transition-transform ${expanded ? "rotate-180" : ""}`}
          >
            <path
              d="M4 6L8 10L12 6"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        {expanded ? (
          <div className="space-y-4 px-5 pb-5">
            {explaining ? (
              <div className="flex items-center gap-2 text-sm text-zinc-500">
                <div className="h-3 w-3 animate-spin rounded-full border border-zinc-600 border-t-zinc-300" />
                Generating explanation...
              </div>
            ) : localExplanation ? (
              <p className="text-sm leading-relaxed text-zinc-400">
                {localExplanation}
              </p>
            ) : (
              <p className="text-sm text-zinc-600">No explanation available.</p>
            )}

            {contradiction.consensus ? (
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.025] p-4">
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                  Evidence Consensus
                </p>
                <p className="text-sm leading-relaxed text-zinc-300">
                  {contradiction.consensus}
                </p>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
