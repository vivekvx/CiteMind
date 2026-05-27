"use client";

export type EvalScores = {
  faithfulness_score: number;
  answer_relevance_score: number;
  context_relevance_score: number;
  citation_coverage_score: number;
};

type EvalCardProps = {
  scores: EvalScores | null;
};

const labels: Array<[keyof EvalScores, string]> = [
  ["faithfulness_score", "Faithfulness"],
  ["answer_relevance_score", "Answer relevance"],
  ["context_relevance_score", "Context relevance"],
  ["citation_coverage_score", "Citation coverage"],
];

export function EvalCard({ scores }: EvalCardProps) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">Evaluation</h2>
      {scores ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {labels.map(([key, label]) => (
            <div className="rounded-md border border-slate-200 p-4" key={key}>
              <p className="text-sm text-slate-500">{label}</p>
              <p className="mt-2 text-2xl font-semibold text-slate-950">
                {scores[key].toFixed(2)}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-4 rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500">
          Run evaluation after receiving an answer.
        </p>
      )}
    </section>
  );
}
