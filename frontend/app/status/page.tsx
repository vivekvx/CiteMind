"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

type ApiHealth = {
  status?: string;
  database?: {
    backend?: string;
    persistent?: boolean;
    production_safe?: boolean;
  };
};

type LlmHealth = {
  configured?: boolean;
  ok?: boolean;
  model?: string;
  base_url?: string;
  chat_completions_url?: string;
  error?: string;
  sample?: string;
};

type ProbeState<T> = {
  data: T | null;
  error: string | null;
  latencyMs: number | null;
};

const emptyProbe = { data: null, error: null, latencyMs: null };

async function probe<T>(path: string): Promise<ProbeState<T>> {
  const startedAt = performance.now();
  try {
    const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    const latencyMs = Math.round(performance.now() - startedAt);
    const data = (await response.json()) as T;

    if (!response.ok) {
      return {
        data,
        error: `HTTP ${response.status}`,
        latencyMs,
      };
    }

    return { data, error: null, latencyMs };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : "Request failed",
      latencyMs: null,
    };
  }
}

function StatusBadge({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${
        ok
          ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-100"
          : "border-amber-300/30 bg-amber-300/10 text-amber-100"
      }`}
    >
      <span
        className={`h-2 w-2 rounded-full ${ok ? "bg-emerald-300" : "bg-amber-300"}`}
      />
      {ok ? "Online" : "Attention"}
    </span>
  );
}

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.045] p-4 shadow-2xl shadow-black/20">
      <p className="text-xs uppercase tracking-[0.24em] text-zinc-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{detail}</p>
    </div>
  );
}

export default function StatusPage() {
  const [apiHealth, setApiHealth] = useState<ProbeState<ApiHealth>>(emptyProbe);
  const [llmHealth, setLlmHealth] = useState<ProbeState<LlmHealth>>(emptyProbe);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    const [apiResult, llmResult] = await Promise.all([
      probe<ApiHealth>("/health"),
      probe<LlmHealth>("/health/llm"),
    ]);
    setApiHealth(apiResult);
    setLlmHealth(llmResult);
    setCheckedAt(new Date());
    setLoading(false);
  }

  useEffect(() => {
    refresh();
  }, []);

  const apiOk = apiHealth.data?.status === "ok" && !apiHealth.error;
  const llmOk = llmHealth.data?.ok === true && !llmHealth.error;
  const database = apiHealth.data?.database;
  const storageOk = database?.production_safe !== false;
  const storageValue = database?.persistent
    ? "Persistent"
    : storageOk
      ? "Local demo"
      : "Blocked";
  const storageDetail = database?.persistent
    ? "Uploads and chunks use durable database storage."
    : storageOk
      ? "SQLite is fine for local development. Hosted Vercel needs Postgres."
      : "Hosted uploads, queries, and deletes are blocked until DATABASE_URL points to Postgres.";
  const overallOk = apiOk && llmOk && storageOk;
  const checkedLabel = useMemo(
    () =>
      checkedAt
        ? checkedAt.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })
        : "Not checked yet",
    [checkedAt],
  );

  return (
    <main className="min-h-screen overflow-hidden px-4 py-6 text-zinc-100 sm:px-6 lg:px-8">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_20%_10%,rgba(255,255,255,0.1),transparent_28rem),linear-gradient(135deg,#090909_0%,#050505_55%,#151515_100%)]" />
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-[0.08] [background-image:linear-gradient(rgba(255,255,255,0.9)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.9)_1px,transparent_1px)] [background-size:44px_44px]" />

      <div className="mx-auto max-w-6xl">
        <header className="relative overflow-hidden rounded-lg border border-white/10 bg-zinc-950/70 p-6 shadow-2xl shadow-black/40 backdrop-blur md:p-8">
          <div className="absolute right-0 top-0 h-32 w-32 border-b border-l border-white/10 bg-white/[0.03]" />
          <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.34em] text-zinc-500">
                CiteMind operations
              </p>
              <h1 className="mt-4 max-w-3xl text-5xl font-semibold tracking-normal text-white [font-family:Georgia,serif] md:text-6xl">
                System Status
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-400">
                A human-readable status view for the same health checks used by
                uptime monitors and deployment verification.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge ok={overallOk} />
              <Link
                className="rounded-md border border-white/15 bg-white/[0.06] px-4 py-2 text-sm font-medium text-zinc-100 hover:border-white/30 hover:bg-white/[0.1]"
                href="/"
              >
                Back to app
              </Link>
            </div>
          </div>
        </header>

        <section className="mt-5 grid gap-4 md:grid-cols-3">
          <MetricCard
            detail="FastAPI health endpoint through the public site proxy."
            label="API"
            value={apiOk ? "Healthy" : "Check needed"}
          />
          <MetricCard
            detail={storageDetail}
            label="Storage"
            value={storageValue}
          />
          <MetricCard
            detail={
              llmHealth.data?.model
                ? `${llmHealth.data.model} via ${llmHealth.data.base_url ?? "configured provider"}`
                : "OpenAI-compatible provider not reported."
            }
            label="LLM"
            value={llmOk ? "Reachable" : "Fallback mode"}
          />
        </section>

        <section className="mt-5 grid gap-4 md:grid-cols-1">
          <MetricCard
            detail={loading ? "Refreshing checks..." : `Last checked at ${checkedLabel}.`}
            label="Latency"
            value={
              apiHealth.latencyMs !== null ? `${apiHealth.latencyMs} ms` : "Pending"
            }
          />
        </section>

        <section className="mt-5 grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-lg border border-white/10 bg-white/[0.045] p-5 shadow-2xl shadow-black/30">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">
                  Public routing
                </p>
                <h2 className="mt-2 text-2xl font-semibold text-white">
                  One website, proxied API
                </h2>
              </div>
              <button
                className="rounded-md border border-white/15 bg-white px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={loading}
                onClick={refresh}
                type="button"
              >
                {loading ? "Checking" : "Refresh"}
              </button>
            </div>

            <div className="mt-6 space-y-3 text-sm text-zinc-300">
              <div className="rounded-md border border-white/10 bg-black/30 p-4">
                <p className="text-zinc-500">User-facing app</p>
                <p className="mt-1 break-all font-mono text-zinc-100">
                  citemind-six.vercel.app
                </p>
              </div>
              <div className="rounded-md border border-white/10 bg-black/30 p-4">
                <p className="text-zinc-500">Health endpoint</p>
                <p className="mt-1 break-all font-mono text-zinc-100">
                  /api/health
                </p>
              </div>
              <div className="rounded-md border border-white/10 bg-black/30 p-4">
                <p className="text-zinc-500">Backend target</p>
                <p className="mt-1 break-all font-mono text-zinc-100">
                  {API_URL}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-white/10 bg-zinc-950/70 p-5 shadow-2xl shadow-black/30">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">
              Raw checks
            </p>
            <pre className="mt-4 max-h-[30rem] overflow-auto rounded-md border border-white/10 bg-black p-4 text-sm leading-6 text-zinc-300 [font-family:ui-monospace,SFMono-Regular,Menlo,monospace]">
              {JSON.stringify(
                {
                  api: apiHealth,
                  llm: llmHealth,
                  checkedAt: checkedAt?.toISOString() ?? null,
                },
                null,
                2,
              )}
            </pre>
          </div>
        </section>
      </div>
    </main>
  );
}
