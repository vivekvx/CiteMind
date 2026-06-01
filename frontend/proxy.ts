import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const acceptsHtml = request.headers.get("accept")?.includes("text/html");

  if (acceptsHtml) {
    return NextResponse.rewrite(new URL("/status", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/api/health", "/api/health/llm"],
};
