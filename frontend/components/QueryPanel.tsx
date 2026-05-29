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
    <section className="rounded-lg border border-white/10 bg-zinc-950/70 p-5 shadow-2xl shadow-black/30 backdrop-blur">
      <h2 className="text-lg font-semibold text-white">Ask research question</h2>
      {activeDocumentTitle ? (
        <p className="mt-2 text-sm text-zinc-400">
          Asking over:{" "}
          <span className="font-medium text-zinc-100">
            {activeDocumentTitle}
          </span>
        </p>
      ) : null}
      <form className="mt-4 space-y-3" onSubmit={submitQuery}>
        <textarea
          className="min-h-32 w-full resize-y rounded-md border border-white/10 bg-black/45 px-3 py-3 text-sm leading-6 text-zinc-100 outline-none placeholder:text-zinc-600 hover:border-white/20 focus:border-white/50 focus:ring-2 focus:ring-white/10"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask a question about the uploaded documents"
          value={query}
        />
        <button
          className="rounded-md bg-white px-4 py-2 text-sm font-medium text-black shadow-lg shadow-black/30 hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500"
          disabled={disabled || isAsking || !query.trim()}
          type="submit"
        >
          {isAsking ? "Asking..." : "Ask"}
        </button>
      </form>
    </section>
  );
}
