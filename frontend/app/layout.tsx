import type { Metadata } from "next";
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
      <body>{children}</body>
    </html>
  );
}
