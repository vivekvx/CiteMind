type EvidenceBarProps = {
  score: number;
  label: string;
};

const SCORE_COLORS = [
  "",
  "bg-red-500/80",
  "bg-orange-500/80",
  "bg-amber-400/80",
  "bg-emerald-400/80",
  "bg-emerald-500",
];

export function EvidenceBar({ score, label }: EvidenceBarProps) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className={`h-1.5 w-3 rounded-full ${
              i <= score
                ? SCORE_COLORS[score] || "bg-zinc-500"
                : "bg-white/[0.08]"
            }`}
          />
        ))}
      </div>
      <span className="text-[11px] font-medium tracking-wide text-zinc-500">
        {label}
      </span>
    </div>
  );
}
