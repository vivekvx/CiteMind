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
  onSelectDocument: (documentId: number) => void;
  onUpload: (file: File) => Promise<void>;
};

export function UploadBox({
  documents,
  selectedDocumentId,
  onSelectDocument,
  onUpload,
}: UploadBoxProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
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

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">Upload document</h2>
      <div className="mt-4 flex flex-col gap-3">
        <input
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
          type="file"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <button
          className="rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          disabled={!file || isUploading}
          onClick={submitUpload}
          type="button"
        >
          {isUploading ? "Uploading..." : "Upload"}
        </button>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold uppercase tracking-normal text-slate-500">
          Uploaded documents
        </h3>
        {selectedDocument ? (
          <p className="mt-2 text-sm text-slate-700">
            Active document:{" "}
            <span className="font-medium text-slate-950">
              {selectedDocument.title}
            </span>
          </p>
        ) : null}
        <div className="mt-3 space-y-3">
          {documents.length === 0 ? (
            <p className="rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500">
              No documents uploaded yet.
            </p>
          ) : (
            documents.map((document) => (
              <button
                className={`w-full rounded-md border p-3 text-left ${
                  document.id === selectedDocumentId
                    ? "border-blue-500 bg-blue-50"
                    : "border-slate-200 bg-white"
                }`}
                key={document.id}
                onClick={() => onSelectDocument(document.id)}
                type="button"
              >
                <h4 className="text-sm font-medium text-slate-900">
                  {document.title}
                </h4>
                {document.abstract ? (
                  <p className="mt-2 line-clamp-3 text-sm text-slate-600">
                    {document.abstract}
                  </p>
                ) : null}
              </button>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
