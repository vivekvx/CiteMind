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
  onUpload: (file: File) => Promise<void>;
};

export function UploadBox({ documents, onUpload }: UploadBoxProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

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
        <div className="mt-3 space-y-3">
          {documents.length === 0 ? (
            <p className="rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500">
              No documents uploaded yet.
            </p>
          ) : (
            documents.map((document) => (
              <article
                className="rounded-md border border-slate-200 p-3"
                key={document.id}
              >
                <h4 className="text-sm font-medium text-slate-900">
                  {document.title}
                </h4>
                {document.abstract ? (
                  <p className="mt-2 line-clamp-3 text-sm text-slate-600">
                    {document.abstract}
                  </p>
                ) : null}
              </article>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
