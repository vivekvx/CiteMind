import Link from "next/link";
import type { DocumentItem } from "../../lib/medical-api";

type DocumentSelectorProps = {
  documents: DocumentItem[];
  selected: Set<number>;
  onToggle: (id: number) => void;
  disabled?: boolean;
};

export function DocumentSelector({
  documents,
  selected,
  onToggle,
  disabled,
}: DocumentSelectorProps) {
  if (documents.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-white/[0.12] bg-white/[0.02] px-5 py-10 text-center">
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          className="mx-auto mb-3 text-zinc-600"
          aria-hidden="true"
        >
          <path
            d="M12 16V4m0 0L8 8m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <p className="text-sm font-medium text-zinc-300">No documents yet</p>
        <p className="mt-1 text-xs text-zinc-500">
          Upload at least two medical papers to compare their claims.
        </p>
        <Link
          href="/research"
          className="mt-4 inline-block rounded-md border border-white/15 bg-white/[0.06] px-4 py-2 text-xs font-medium text-zinc-200 hover:border-white/30 hover:bg-white/[0.1]"
        >
          Upload papers
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => {
        const isSelected = selected.has(doc.id);
        return (
          <button
            key={doc.id}
            type="button"
            disabled={disabled}
            onClick={() => onToggle(doc.id)}
            className={`group flex w-full items-start gap-3 rounded-lg border px-4 py-3 text-left transition-all ${
              isSelected
                ? "border-white/30 bg-white/[0.08]"
                : "border-white/[0.08] bg-white/[0.025] hover:border-white/[0.16] hover:bg-white/[0.045]"
            } ${disabled ? "pointer-events-none opacity-50" : ""}`}
          >
            <div
              className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
                isSelected
                  ? "border-white/60 bg-white/90"
                  : "border-white/20 bg-transparent"
              }`}
            >
              {isSelected ? (
                <svg
                  width="10"
                  height="8"
                  viewBox="0 0 10 8"
                  fill="none"
                  className="text-black"
                >
                  <path
                    d="M1 4L3.5 6.5L9 1"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : null}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-zinc-200">
                {doc.title}
              </p>
              {doc.abstract ? (
                <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-zinc-500">
                  {doc.abstract}
                </p>
              ) : null}
            </div>
          </button>
        );
      })}
    </div>
  );
}
