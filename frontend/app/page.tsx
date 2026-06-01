"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnswerCard, QueryAnswer } from "../components/AnswerCard";
import { EvalCard, EvalScores } from "../components/EvalCard";
import { QueryPanel } from "../components/QueryPanel";
import { DocumentItem, UploadBox } from "../components/UploadBox";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

type LlmHealth = {
  configured: boolean;
  ok: boolean;
  model: string;
  base_url?: string;
  chat_completions_url?: string;
  error?: string;
};

type ApiError = {
  detail?: string;
};

export default function Home() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [answer, setAnswer] = useState<QueryAnswer | null>(null);
  const [query, setQuery] = useState("");
  const [evalScores, setEvalScores] = useState<EvalScores | null>(null);
  const [llmHealth, setLlmHealth] = useState<LlmHealth | null>(null);
  const [status, setStatus] = useState("");
  const selectedDocument =
    documents.find((document) => document.id === selectedDocumentId) ?? null;

  async function loadDocuments(preferredDocumentId?: number) {
    const response = await fetch(`${API_URL}/documents`);
    if (!response.ok) {
      throw new Error("Unable to load documents");
    }
    const nextDocuments: DocumentItem[] = await response.json();
    setDocuments(nextDocuments);
    setSelectedDocumentId((currentDocumentId) => {
      if (nextDocuments.length === 0) {
        return null;
      }
      if (
        preferredDocumentId &&
        nextDocuments.some((document) => document.id === preferredDocumentId)
      ) {
        return preferredDocumentId;
      }
      if (
        currentDocumentId &&
        nextDocuments.some((document) => document.id === currentDocumentId)
      ) {
        return currentDocumentId;
      }
      return nextDocuments[0].id;
    });
  }

  useEffect(() => {
    loadDocuments().catch(() => setStatus("Could not load documents."));
    fetch(`${API_URL}/health/llm`)
      .then((response) => (response.ok ? response.json() : null))
      .then((health: LlmHealth | null) => setLlmHealth(health))
      .catch(() => setLlmHealth(null));
  }, []);

  async function handleUpload(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    setStatus("Uploading document...");
    const response = await fetch(`${API_URL}/documents/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      setStatus(await errorMessage(response, "Upload failed."));
      return;
    }
    const uploadedDocument = (await response.json()) as { id: number };
    await loadDocuments(uploadedDocument.id);
    setStatus("Document uploaded.");
  }

  async function handleDeleteDocument(documentId: number) {
    const response = await fetch(`${API_URL}/documents/${documentId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      setStatus(await errorMessage(response, "Could not delete document."));
      return;
    }
    if (selectedDocumentId === documentId) {
      setAnswer(null);
      setEvalScores(null);
    }
    await loadDocuments();
    setStatus("Document deleted.");
  }

  async function handleResetDemo() {
    setStatus("Resetting demo data...");
    const response = await fetch(`${API_URL}/documents/demo/reset`, {
      method: "POST",
    });
    if (!response.ok) {
      setStatus(await errorMessage(response, "Could not reset demo data."));
      return;
    }
    const demoDocument = (await response.json()) as { id: number };
    setAnswer(null);
    setEvalScores(null);
    setQuery("");
    await loadDocuments(demoDocument.id);
    setStatus("Demo reset with sample_ai_report.md.");
  }

  async function handleQuery(nextQuery: string) {
    if (!selectedDocumentId) {
      setStatus("Select a document before asking.");
      return;
    }
    const currentDocumentId = selectedDocumentId;
    try {
      await loadDocuments(currentDocumentId);
      const response = await fetch(`${API_URL}/documents`, { cache: "no-store" });
      if (response.ok) {
        const latestDocuments: DocumentItem[] = await response.json();
        if (!latestDocuments.some((document) => document.id === currentDocumentId)) {
          setAnswer(null);
          setEvalScores(null);
          setStatus("That document is no longer available. Upload it again before asking.");
          return;
        }
      }
    } catch {
      setStatus("Could not refresh document context.");
      return;
    }
    setQuery(nextQuery);
    setEvalScores(null);
    setStatus("Retrieving answer...");
    const response = await fetch(`${API_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: nextQuery,
        document_ids: selectedDocumentId ? [selectedDocumentId] : undefined,
      }),
    });
    if (!response.ok) {
      setStatus(await errorMessage(response, "Query failed."));
      return;
    }
    setAnswer(await response.json());
    setStatus("Answer ready.");
  }

  async function handleEval() {
    if (!answer) {
      return;
    }
    setStatus("Running evaluation...");
    const response = await fetch(`${API_URL}/evals/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        answer: answer.answer,
        contexts: answer.citations.map((citation) => citation.text),
        citations: answer.citations,
      }),
    });
    if (!response.ok) {
      setStatus(await errorMessage(response, "Evaluation failed."));
      return;
    }
    setEvalScores(await response.json());
    setStatus("Evaluation complete.");
  }

  return (
    <main className="min-h-screen px-4 py-6 text-zinc-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-lg border border-white/10 bg-white/[0.045] px-5 py-5 shadow-2xl shadow-black/30 backdrop-blur md:px-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">
                Document-aware research
              </p>
              <h1 className="mt-2 text-4xl font-semibold tracking-normal text-white">
                CiteMind
              </h1>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                className="rounded-md border border-white/15 bg-white/[0.06] px-3 py-2 text-xs font-medium text-zinc-200 hover:border-white/30 hover:bg-white/[0.1]"
                href="/status"
              >
                System status
              </Link>
              <div className="rounded-md border border-white/10 bg-black/30 px-3 py-2 text-xs text-zinc-400">
                API: {API_URL.replace("http://", "")}
              </div>
            </div>
          </div>
          <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-400">
            Citation-first AI research assistant with RAG evaluation
          </p>
        </header>

        {status ? (
          <div className="rounded-md border border-white/10 bg-white/[0.06] px-4 py-3 text-sm text-zinc-200 shadow-lg shadow-black/20">
            {status}
          </div>
        ) : null}

        {llmHealth && !llmHealth.ok ? (
          <div className="rounded-md border border-white/10 bg-zinc-950/80 px-4 py-3 text-sm text-zinc-300 shadow-lg shadow-black/25">
            <span className="font-medium text-white">LLM synthesis unavailable</span>
            {llmHealth.error ? `: ${llmHealth.error}` : ""}. CiteMind will use local
            fallback answers until the configured OpenAI-compatible provider is reachable.
          </div>
        ) : null}

        <div className="grid gap-5 lg:grid-cols-[minmax(20rem,0.88fr)_minmax(0,1.12fr)]">
          <UploadBox
            documents={documents}
            onDeleteDocument={handleDeleteDocument}
            onResetDemo={handleResetDemo}
            onSelectDocument={setSelectedDocumentId}
            onUpload={handleUpload}
            selectedDocumentId={selectedDocumentId}
          />

          <section className="space-y-6">
            <QueryPanel
              activeDocumentTitle={selectedDocument?.title}
              disabled={!selectedDocumentId}
              onSubmit={handleQuery}
            />
            <AnswerCard answer={answer} onRunEval={handleEval} />
            <EvalCard scores={evalScores} />
          </section>
        </div>
      </div>
    </main>
  );
}

async function errorMessage(response: Response, fallback: string) {
  try {
    const payload = (await response.json()) as ApiError;
    return payload.detail || fallback;
  } catch {
    return fallback;
  }
}
