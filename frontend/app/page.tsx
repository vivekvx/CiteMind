import Link from "next/link";

const PIPELINE_STEPS = [
  {
    title: "Extract Claims",
    description:
      "An LLM reads each paper and pulls out structured medical claims: drug, condition, outcome, direction, population, and study design.",
  },
  {
    title: "Grade Evidence",
    description:
      "Every claim is scored on the GRADE hierarchy. Meta-analyses rank highest, then RCTs, cohorts, case-control, and case series.",
  },
  {
    title: "Detect Contradictions",
    description:
      "Claims about the same drug and condition are compared. Opposing directions are classified as direct, methodological, partial, or temporal conflicts.",
  },
  {
    title: "Generate Consensus",
    description:
      "For each conflict, the system weighs evidence quality and produces a consensus statement a clinician can act on.",
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen px-4 py-10 text-zinc-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl space-y-16">
        {/* Hero */}
        <section className="animate-rise pt-8 text-center sm:pt-16">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">
            MedContradict
          </p>
          <h1 className="mx-auto mt-4 max-w-3xl text-4xl font-semibold leading-tight tracking-tight text-white sm:text-5xl">
            Medical papers contradict each other.
            <br />
            <span className="text-zinc-400">CiteMind finds where.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-zinc-400">
            Upload clinical studies and CiteMind extracts their claims, grades
            the evidence, and surfaces the contradictions — with an explanation
            of why the findings diverge and what the balance of evidence says.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/contradictions"
              className="rounded-md bg-white px-6 py-3 text-sm font-semibold text-black shadow-lg shadow-black/30 hover:bg-zinc-200"
            >
              Try the demo
            </Link>
            <Link
              href="/research"
              className="rounded-md border border-white/15 bg-white/[0.06] px-6 py-3 text-sm font-medium text-zinc-200 hover:border-white/30 hover:bg-white/[0.1]"
            >
              Document Q&amp;A
            </Link>
          </div>
        </section>

        {/* Pipeline */}
        <section>
          <h2 className="text-center text-2xl font-semibold tracking-tight text-white">
            How it works
          </h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            {PIPELINE_STEPS.map((step, i) => (
              <div
                key={step.title}
                className={`card-hover animate-rise-${i + 1} rounded-lg border border-white/10 bg-white/[0.035] p-6`}
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/[0.08] text-xs font-semibold text-zinc-300">
                    {i + 1}
                  </span>
                  <h3 className="text-base font-semibold text-white">
                    {step.title}
                  </h3>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-zinc-400">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Example strip */}
        <section className="rounded-lg border border-white/10 bg-zinc-950/70 p-6 sm:p-8">
          <h2 className="text-lg font-semibold text-white">
            A real conflict it catches
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-zinc-400">
            A 4,200-patient randomized trial reports atorvastatin cuts
            cardiovascular mortality by 28%. A cohort of 890 elderly patients
            finds no benefit and more myopathy. Same drug, same condition,
            opposite conclusions. CiteMind flags it as a high-severity direct
            contradiction and explains the population difference driving it.
          </p>
          <Link
            href="/contradictions"
            className="mt-5 inline-block rounded-md border border-white/15 bg-white/[0.06] px-4 py-2 text-sm font-medium text-zinc-200 hover:border-white/30 hover:bg-white/[0.1]"
          >
            See the analysis
          </Link>
        </section>

        {/* Footer note */}
        <footer className="border-t border-white/[0.06] pb-8 pt-6 text-center text-xs text-zinc-600">
          CiteMind — citation-first research with RAG evaluation. Built with
          FastAPI, Next.js, Qdrant, and BGE-M3 embeddings.
        </footer>
      </div>
    </main>
  );
}
