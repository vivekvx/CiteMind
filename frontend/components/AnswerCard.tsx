"use client";

export type QueryCitation = {
  document_id: number;
  chunk_index: number;
  text: string;
};

export type QueryAnswer = {
  answer: string;
  citations: QueryCitation[];
};

type AnswerCardProps = {
  answer: QueryAnswer | null;
  onRunEval: () => Promise<void>;
};

export function AnswerCard({ answer, onRunEval }: AnswerCardProps) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold">Answer</h2>
        <button
          className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          disabled={!answer}
          onClick={onRunEval}
          type="button"
        >
          Run evaluation
        </button>
      </div>

      {answer ? (
        <div className="mt-4 space-y-5">
          <p className="rounded-md bg-slate-50 p-4 text-sm leading-6 text-slate-800">
            {answer.answer}
          </p>

          <div>
            <h3 className="text-sm font-semibold uppercase tracking-normal text-slate-500">
              Citations
            </h3>
            <div className="mt-3 space-y-2">
              {answer.citations.length === 0 ? (
                <p className="text-sm text-slate-500">No citations returned.</p>
              ) : (
                answer.citations.map((citation) => (
                  <div
                    className="rounded-md border border-slate-200 p-3 text-sm"
                    key={`${citation.document_id}-${citation.chunk_index}`}
                  >
                    Document {citation.document_id}, chunk {citation.chunk_index}
                  </div>
                ))
              )}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold uppercase tracking-normal text-slate-500">
              Retrieved chunks
            </h3>
            <div className="mt-3 space-y-3">
              {answer.citations.map((citation) => (
                <blockquote
                  className="rounded-md border-l-4 border-blue-600 bg-blue-50 p-3 text-sm leading-6 text-slate-700"
                  key={`chunk-${citation.document_id}-${citation.chunk_index}`}
                >
                  {citation.text}
                </blockquote>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <p className="mt-4 rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500">
          Ask a question to see an answer, citations, and retrieved chunks.
        </p>
      )}
    </section>
  );
}
