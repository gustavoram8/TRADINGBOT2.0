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

  try {
    const res = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        {
          error: `El servidor Python respondió con error HTTP ${res.status}: ${text || res.statusText}`,
          diagnostic: {
            step: "python_api_response",
            backend_url: backendUrl,
            http_status: res.status,
            body: text.slice(0, 500),
          },
        },
        { status: res.status }
      );
    }

    // Read Python's response body in the background while streaming our own
    // keepalive "\n" bytes to nginx/browser every 5s.  This keeps every layer
    // of the chain alive regardless of proxy buffering mode or network policy.
    const chunks: Uint8Array[] = [];
    let pyDone = false;
    let pyErr: string | null = null;

    const readPromise = (async () => {
      try {
        const reader = res.body!.getReader();
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          if (value) chunks.push(value);
        }
      } catch (e) {
        pyErr = String(e);
      } finally {
        pyDone = true;
      }
    })();

    const enc = new TextEncoder();

    const stream = new ReadableStream<Uint8Array>({
      async start(ctrl) {
        // Keep connections alive while Python processes
        while (!pyDone) {
          const winner = await Promise.race([
            readPromise.then(() => "done" as const),
            new Promise<"tick">((r) => setTimeout(() => r("tick"), 5000)),
          ]);
          if (winner === "tick") ctrl.enqueue(enc.encode("\n"));
        }

        if (pyErr !== null) {
          ctrl.enqueue(enc.encode(JSON.stringify({
            error: `Error leyendo respuesta de Python: ${pyErr}`,
            diagnostic: { step: "reading_python_body" },
          })));
          ctrl.close();
          return;
        }

        // Reassemble and validate the full response
        const totalLen = chunks.reduce((s, c) => s + c.length, 0);
        const buf = new Uint8Array(totalLen);
        let off = 0;
        for (const c of chunks) { buf.set(c, off); off += c.length; }
        const full = new TextDecoder().decode(buf).trim();

        if (!full) {
          ctrl.enqueue(enc.encode(JSON.stringify({
            error: "El servidor Python cerró la conexión sin devolver datos.",
            diagnostic: { step: "empty_python_response" },
          })));
        } else {
          try {
            JSON.parse(full); // validate before forwarding
            ctrl.enqueue(enc.encode(full));
          } catch {
            ctrl.enqueue(enc.encode(JSON.stringify({
              error: "El servidor Python devolvió una respuesta inválida (no es JSON).",
              diagnostic: { step: "invalid_python_json", raw_preview: full.slice(0, 300) },
            })));
          }
        }
        ctrl.close();
      },
    });

    return new Response(stream, { headers: { "Content-Type": "application/json" } });
  } catch (err) {
    clearTimeout(timeoutId);
    const isAbort = err instanceof Error && err.name === "AbortError";
    const isNetworkError = err instanceof TypeError && String(err).includes("fetch");
    return NextResponse.json(
      {
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
      },
      { status: isAbort ? 504 : 502 }
    );
  }
}
