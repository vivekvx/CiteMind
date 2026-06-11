import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "CiteMind",
  description: "Citation-first AI research assistant with RAG evaluation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <nav className="border-b border-white/[0.06] bg-black/40 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3 sm:px-6 lg:px-8">
            <Link
              href="/"
              className="text-sm font-semibold tracking-tight text-white"
            >
              CiteMind
            </Link>
            <div className="flex items-center gap-1">
              <Link
                href="/"
                className="rounded-md px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-white/[0.06] hover:text-zinc-200"
              >
                Research
              </Link>
              <Link
                href="/contradictions"
                className="rounded-md px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-white/[0.06] hover:text-zinc-200"
              >
                Contradictions
              </Link>
              <Link
                href="/status"
                className="rounded-md px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-white/[0.06] hover:text-zinc-200"
              >
                Status
              </Link>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
