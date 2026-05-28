"use client";

import { FormEvent, useState } from "react";

type QueryPanelProps = {
  activeDocumentTitle?: string;
  disabled?: boolean;
  onSubmit: (query: string) => Promise<void>;
};

export function QueryPanel({
  activeDocumentTitle,
  disabled = false,
  onSubmit,
}: QueryPanelProps) {
  const [query, setQuery] = useState("");
  const [isAsking, setIsAsking] = useState(false);

  async function submitQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || disabled) {
      return;
    }
    setIsAsking(true);
    await onSubmit(trimmed);
    setIsAsking(false);
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">Ask research question</h2>
      {activeDocumentTitle ? (
        <p className="mt-2 text-sm text-slate-600">
          Asking over:{" "}
          <span className="font-medium text-slate-900">
            {activeDocumentTitle}
          </span>
        </p>
      ) : null}
      <form className="mt-4 space-y-3" onSubmit={submitQuery}>
        <textarea
          className="min-h-28 w-full resize-y rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask a question about the uploaded documents"
          value={query}
        />
        <button
          className="rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          disabled={disabled || isAsking || !query.trim()}
          type="submit"
        >
          {isAsking ? "Asking..." : "Ask"}
        </button>
      </form>
    </section>
  );
}
