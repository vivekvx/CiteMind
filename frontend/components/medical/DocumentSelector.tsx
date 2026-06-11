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
      <div className="rounded-lg border border-dashed border-white/[0.12] bg-white/[0.02] px-5 py-8 text-center">
        <p className="text-sm text-zinc-500">
          No documents uploaded yet. Upload papers from the home page first.
        </p>
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
