import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Diagnostic endpoint: sleeps N seconds (default 90) then returns.
// Sends "\n" keepalive bytes every 5s so intermediate timeouts don't drop the connection.
// Hit: GET /api/sleep?s=90
export async function GET(req: Request) {
  const url = new URL(req.url);
  const s = Math.min(parseInt(url.searchParams.get("s") ?? "90", 10) || 90, 540);
  const t0 = Date.now();

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      let remainingMs = s * 1000;
      while (remainingMs > 5000) {
        await new Promise<void>((r) => setTimeout(r, 5000));
        remainingMs -= 5000;
        controller.enqueue(encoder.encode("\n"));
      }
      if (remainingMs > 0) {
        await new Promise<void>((r) => setTimeout(r, remainingMs));
      }
      controller.enqueue(
        encoder.encode(
          JSON.stringify({ ok: true, slept_ms: Date.now() - t0, slept_seconds: s }),
        ),
      );
      controller.close();
    },
  });

  return new Response(stream, { headers: { "Content-Type": "application/json" } });
}
