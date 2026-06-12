import type { Metadata } from "next";
import { Inter, Inter_Tight } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const interTight = Inter_Tight({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CiteMind — Medical Contradiction Detection",
  description:
    "CiteMind extracts claims from clinical papers, grades the evidence, and finds where studies contradict each other.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${interTight.variable}`}>
      <body>
        <nav className="sticky top-0 z-40 border-b border-white/[0.06] bg-black/60 backdrop-blur-md">
          <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3 sm:px-6 lg:px-8">
            <Link
              href="/"
              className="font-display text-sm font-semibold tracking-tight text-white"
            >
              CiteMind
            </Link>
            <div className="flex items-center gap-1">
              <Link
                href="/research"
                className="rounded-md px-3 py-1.5 text-xs font-medium text-zinc-400 transition-colors hover:bg-white/[0.06] hover:text-zinc-100"
              >
                Research
              </Link>
              <Link
                href="/contradictions"
                className="rounded-md px-3 py-1.5 text-xs font-medium text-zinc-400 transition-colors hover:bg-white/[0.06] hover:text-zinc-100"
              >
                Contradictions
              </Link>
              <Link
                href="/status"
                className="rounded-md px-3 py-1.5 text-xs font-medium text-zinc-400 transition-colors hover:bg-white/[0.06] hover:text-zinc-100"
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
