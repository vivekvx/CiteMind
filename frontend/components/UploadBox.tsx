"use client";

import { useState } from "react";

export type DocumentItem = {
  id: number;
  title: string;
  source_url?: string | null;
  abstract?: string | null;
  created_at: string;
  updated_at: string;
};

type UploadBoxProps = {
  documents: DocumentItem[];
  selectedDocumentId: number | null;
  onDeleteDocument: (documentId: number) => Promise<void>;
  onResetDemo: () => Promise<void>;
  onSelectDocument: (documentId: number) => void;
  onUpload: (file: File) => Promise<void>;
};

export function UploadBox({
  documents,
  selectedDocumentId,
  onDeleteDocument,
  onResetDemo,
  onSelectDocument,
  onUpload,
}: UploadBoxProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const selectedDocument = documents.find(
    (document) => document.id === selectedDocumentId,
  );

  async function submitUpload() {
    if (!file) {
      return;
    }
    setIsUploading(true);
    await onUpload(file);
    setFile(null);
    setIsUploading(false);
  }

  async function resetDemo() {
    setIsResetting(true);
    try {
      await onResetDemo();
      setFile(null);
    } finally {
      setIsResetting(false);
    }
  }

  return (
    <section className="rounded-lg border border-white/10 bg-zinc-950/70 p-5 shadow-2xl shadow-black/30 backdrop-blur">
      <h2 className="text-lg font-semibold text-white">Upload document</h2>
      <div className="mt-4 flex flex-col gap-3">
        <input
          className="rounded-md border border-white/10 bg-black/40 px-3 py-2 text-sm text-zinc-200 file:mr-3 file:rounded-md file:border-0 file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-black hover:border-white/20"
          type="file"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <button
          className="rounded-md bg-white px-4 py-2 text-sm font-medium text-black shadow-lg shadow-black/30 hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500"
          disabled={!file || isUploading}
          onClick={submitUpload}
          type="button"
        >
          {isUploading ? "Uploading..." : "Upload"}
        </button>
        <button
          className="rounded-md border border-white/10 bg-black/30 px-4 py-2 text-sm font-medium text-zinc-300 hover:border-white/25 hover:text-white disabled:cursor-not-allowed disabled:border-white/5 disabled:text-zinc-600"
          disabled={isResetting}
          onClick={resetDemo}
          type="button"
        >
          {isResetting ? "Resetting demo..." : "Reset demo sample"}
        </button>
      </div>

      <div className="mt-6">
        <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">
          Uploaded documents
        </h3>
        {selectedDocument ? (
          <p className="mt-2 text-sm text-zinc-400">
            Active document:{" "}
            <span className="font-medium text-white">
              {selectedDocument.title}
            </span>
          </p>
        ) : null}
        <div className="mt-3 space-y-3">
          {documents.length === 0 ? (
            <p className="rounded-md border border-dashed border-white/15 bg-white/[0.03] p-4 text-sm text-zinc-500">
              No documents uploaded yet.
            </p>
          ) : (
            documents.map((document) => (
              <div
                className={`w-full rounded-md border p-3 text-left shadow-lg shadow-black/20 ${
                  document.id === selectedDocumentId
                    ? "border-white/40 bg-white/[0.09]"
                    : "border-white/10 bg-white/[0.035] hover:border-white/20 hover:bg-white/[0.055]"
                }`}
                key={document.id}
              >
                <button
                  className="w-full text-left"
                  onClick={() => onSelectDocument(document.id)}
                  type="button"
                >
                  <h4 className="text-sm font-medium text-zinc-100">
                    {document.title}
                  </h4>
                </button>
                {document.abstract ? (
                  <p className="mt-2 line-clamp-3 text-sm leading-6 text-zinc-500">
                    {document.abstract}
                  </p>
                ) : null}
                <button
                  className="mt-3 text-sm font-medium text-zinc-400 hover:text-white"
                  onClick={() => onDeleteDocument(document.id)}
                  type="button"
                >
                  Delete
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
