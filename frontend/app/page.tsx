"use client";

import { useEffect, useState } from "react";
import { AnswerCard, QueryAnswer } from "../components/AnswerCard";
import { EvalCard, EvalScores } from "../components/EvalCard";
import { QueryPanel } from "../components/QueryPanel";
import { DocumentItem, UploadBox } from "../components/UploadBox";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export default function Home() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [answer, setAnswer] = useState<QueryAnswer | null>(null);
  const [query, setQuery] = useState("");
  const [evalScores, setEvalScores] = useState<EvalScores | null>(null);
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
      setStatus("Upload failed.");
      return;
    }
    const uploadedDocument = (await response.json()) as { id: number };
    await loadDocuments(uploadedDocument.id);
    setStatus("Document uploaded.");
  }

  async function handleQuery(nextQuery: string) {
    if (!selectedDocumentId) {
      setStatus("Select a document before asking.");
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
      setStatus("Query failed.");
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
      setStatus("Evaluation failed.");
      return;
    }
    setEvalScores(await response.json());
    setStatus("Evaluation complete.");
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-950 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="border-b border-slate-200 pb-6">
          <h1 className="text-4xl font-semibold tracking-normal">CiteMind</h1>
          <p className="mt-2 max-w-2xl text-base text-slate-600">
            Citation-first AI research assistant with RAG evaluation
          </p>
        </header>

        {status ? (
          <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
            {status}
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <UploadBox
            documents={documents}
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
