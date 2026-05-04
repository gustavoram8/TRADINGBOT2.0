import { NextRequest, NextResponse } from "next/server";
import { generateMockBacktestResult, DEFAULT_CONFIG } from "@/lib/mock-data";
import type { BotConfig } from "@/lib/types";

const PYTHON_API = process.env.PYTHON_API_URL ?? "";

export async function POST(req: NextRequest) {
  const body = await req.json() as {
    start_date?: string;
    end_date?: string;
    interval?: string;
    config?: BotConfig;
    [key: string]: unknown;
  };

  if (!PYTHON_API) {
    const startDate = body.start_date ?? "2025-10-01";
    const endDate   = body.end_date   ?? "2025-11-30";
    const interval  = body.interval   ?? "1h";
    const config    = body.config     ?? DEFAULT_CONFIG;
    return NextResponse.json(
      generateMockBacktestResult(startDate, endDate, interval, config)
    );
  }

  const backendUrl = `${PYTHON_API}/backtest`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000); // 10 min

  // Use a TransformStream so we can write keepalive "\n" bytes from Node.js
  // directly — bypassing any gzip compression or Python-to-Node buffering that
  // would otherwise swallow them before they reach nginx/browser.
  const { readable, writable } = new TransformStream<Uint8Array, Uint8Array>();
  const writer = writable.getWriter();
  const enc = new TextEncoder();

  let keepaliveTimer: ReturnType<typeof setInterval> | null = setInterval(() => {
    writer.write(enc.encode("\n")).catch(() => stopKeepalive());
  }, 5000);

  const stopKeepalive = () => {
    if (keepaliveTimer !== null) {
      clearInterval(keepaliveTimer);
      keepaliveTimer = null;
    }
  };

  // Fetch Python in the background; write result (or error JSON) then close stream.
  void (async () => {
    try {
      const res = await fetch(backendUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      stopKeepalive();

      if (!res.ok) {
        const text = await res.text();
        await writer.write(enc.encode(JSON.stringify({
          error: `El servidor Python respondió con error HTTP ${res.status}: ${text || res.statusText}`,
          diagnostic: {
            step: "python_api_response",
            backend_url: backendUrl,
            http_status: res.status,
            body: text.slice(0, 500),
          },
        })));
      } else {
        // Buffer the full Python response; keepalives already kept the
        // browser connection alive during the wait.
        const text = await res.text();
        await writer.write(enc.encode(text));
      }
    } catch (err) {
      clearTimeout(timeoutId);
      stopKeepalive();
      const isAbort = err instanceof Error && err.name === "AbortError";
      const isNetworkError = err instanceof TypeError && String(err).includes("fetch");
      await writer.write(enc.encode(JSON.stringify({
        error: isAbort
          ? `El backtest superó el tiempo máximo (10 min) sin respuesta del servidor Python.`
          : isNetworkError
          ? `No se pudo conectar con el servidor Python en ${backendUrl}. ¿Está corriendo uvicorn?`
          : `Error inesperado al llamar el backend: ${String(err)}`,
        diagnostic: {
          step: "next_to_python_fetch",
          backend_url: backendUrl,
          PYTHON_API_URL_set: !!process.env.PYTHON_API_URL,
          error_type: err instanceof Error ? err.constructor.name : typeof err,
          error_detail: String(err),
        },
      })));
    } finally {
      await writer.close().catch(() => {});
    }
  })();

  return new Response(readable, {
    headers: {
      "Content-Type": "application/json",
      // Tell nginx not to buffer this streaming response.
      "X-Accel-Buffering": "no",
      // Prevent Next.js compression middleware from buffering keepalive chunks.
      "Cache-Control": "no-transform, no-store",
    },
  });
}
