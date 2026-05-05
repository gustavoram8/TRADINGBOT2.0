import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Diagnostic endpoint: sleeps N seconds (default 90) then returns.
// Used to verify nginx timeout config without involving Python.
// Hit: GET /api/sleep?s=90
export async function GET(req: Request) {
  const url = new URL(req.url);
  const s = Math.min(parseInt(url.searchParams.get("s") ?? "90", 10) || 90, 540);
  const t0 = Date.now();
  await new Promise((r) => setTimeout(r, s * 1000));
  return NextResponse.json({
    ok: true,
    slept_ms: Date.now() - t0,
    slept_seconds: s,
  });
}
