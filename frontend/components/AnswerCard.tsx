"use client";

import { useState } from "react";

export type QueryCitation = {
  document_id: number;
  chunk_index: number;
  text: string;
};

export type QueryAnswer = {
  query_id?: number;
  answer: string;
  citations: QueryCitation[];
  retrieved_chunks?: QueryCitation[];
  document_ids_used?: number[];
  intent?: string;
  requested_count?: number;
  used_llm?: boolean;
  retrieved_chunk_count?: number;
  retrieval_strategy?: string;
  retrieval_comparison?: Record<string, number>;
};

type AnswerCardProps = {
  answer: QueryAnswer | null;
  onRunEval: () => Promise<void>;
};

export function AnswerCard({ answer, onRunEval }: AnswerCardProps) {
  const [showAllChunks, setShowAllChunks] = useState(false);
  const retrievedChunks = answer?.retrieved_chunks ?? answer?.citations ?? [];
  const visibleChunks = showAllChunks ? retrievedChunks : retrievedChunks.slice(0, 3);

  return (
    <section className="rounded-lg border border-white/10 bg-zinc-950/70 p-5 shadow-2xl shadow-black/30 backdrop-blur">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold text-white">Answer</h2>
        <button
          className="rounded-md border border-white/15 bg-white/[0.08] px-4 py-2 text-sm font-medium text-zinc-100 shadow-lg shadow-black/20 hover:border-white/30 hover:bg-white/[0.12] disabled:cursor-not-allowed disabled:border-white/5 disabled:bg-zinc-900 disabled:text-zinc-600"
          disabled={!answer}
          onClick={onRunEval}
          type="button"
        >
          Run evaluation
        </button>
      </div>

      {answer ? (
        <div className="mt-4 space-y-5">
          <div className="flex flex-wrap gap-2 text-xs font-medium">
            <span
              className={`rounded-md px-2 py-1 ${
                answer.used_llm
                  ? "border border-white/20 bg-white text-black"
                  : "border border-white/10 bg-white/[0.07] text-zinc-300"
              }`}
            >
              {answer.used_llm ? "LLM synthesis" : "Local fallback"}
            </span>
            {answer.intent ? (
              <span className="rounded-md border border-white/10 bg-white/[0.045] px-2 py-1 text-zinc-400">
                Intent: {answer.intent.replaceAll("_", " ")}
              </span>
            ) : null}
            {typeof answer.retrieved_chunk_count === "number" ? (
              <span className="rounded-md border border-white/10 bg-white/[0.045] px-2 py-1 text-zinc-400">
                Chunks: {answer.retrieved_chunk_count}
              </span>
            ) : null}
            {answer.retrieval_strategy ? (
              <span className="rounded-md border border-white/10 bg-white/[0.045] px-2 py-1 text-zinc-400">
                Retrieval: {answer.retrieval_strategy}
              </span>
            ) : null}
            {answer.retrieval_comparison?.baseline_chunks ? (
              <span className="rounded-md border border-white/10 bg-white/[0.045] px-2 py-1 text-zinc-400">
                Baseline {answer.retrieval_comparison.baseline_chunks}
                {answer.retrieval_comparison.pageindex_chunks
                  ? ` / PageIndex ${answer.retrieval_comparison.pageindex_chunks}`
                  : ""}
              </span>
            ) : null}
          </div>

          <div className="whitespace-pre-wrap rounded-md border border-white/10 bg-black/35 p-4 text-sm leading-6 text-zinc-200">
            {answer.answer}
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">
              Citations
            </h3>
            <div className="mt-3 space-y-2">
              {answer.citations.length === 0 ? (
                <p className="text-sm text-zinc-500">No citations returned.</p>
              ) : (
                answer.citations.map((citation) => (
                  <div
                    className="rounded-md border border-white/10 bg-white/[0.035] p-3 text-sm text-zinc-300"
                    key={`${citation.document_id}-${citation.chunk_index}`}
                  >
                    Document {citation.document_id}, chunk {citation.chunk_index}
                  </div>
                ))
              )}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">
                Retrieved chunks
              </h3>
              {retrievedChunks.length > 3 ? (
                <button
                  className="text-sm font-medium text-zinc-400 hover:text-white"
                  onClick={() => setShowAllChunks((current) => !current)}
                  type="button"
                >
                  {showAllChunks ? "Show fewer" : "Show more"}
                </button>
              ) : null}
            </div>
            <div className="mt-3 space-y-3">
              {visibleChunks.map((citation) => (
                <blockquote
                  className="rounded-md border border-white/10 border-l-white/40 bg-white/[0.035] p-3 text-sm leading-6 text-zinc-400"
                  key={`chunk-${citation.document_id}-${citation.chunk_index}`}
                >
                  {citation.text}
                </blockquote>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <p className="mt-4 rounded-md border border-dashed border-white/15 bg-white/[0.03] p-4 text-sm text-zinc-500">
          Ask a question to see an answer, citations, and retrieved chunks.
        </p>
      )}
    </section>
  );
}
