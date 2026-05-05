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
  const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000);

  let res: Response;
  try {
    res = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
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
          error_type: err instanceof Error ? err.constructor.name : typeof err,
          error_detail: String(err),
        },
      },
      { status: isAbort ? 504 : 502 }
    );
  }

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

  // CRITICAL: start() must be synchronous so the stream becomes "readable"
  // immediately and the HTTP layer starts flushing bytes to nginx/browser.
  // The async work runs in a background task that captures `ctrl`.
  const enc = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    start(ctrl) {
      // Send a newline immediately so nginx/browser see bytes right away.
      ctrl.enqueue(enc.encode("\n"));

      void (async () => {
        const chunks: Uint8Array[] = [];
        let pyErr: string | null = null;
        let pyDone = false;

        const readTask = (async () => {
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

        // Keepalive: enqueue "\n" every 5s until Python finishes.
        while (!pyDone) {
          await Promise.race([
            readTask,
            new Promise((r) => setTimeout(r, 5000)),
          ]);
          if (!pyDone) {
            try { ctrl.enqueue(enc.encode("\n")); } catch { return; }
          }
        }

        // Send the final payload.
        try {
          if (pyErr !== null) {
            ctrl.enqueue(enc.encode(JSON.stringify({
              error: `Error leyendo respuesta de Python: ${pyErr}`,
              diagnostic: { step: "reading_python_body" },
            })));
          } else {
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
                JSON.parse(full);
                ctrl.enqueue(enc.encode(full));
              } catch {
                ctrl.enqueue(enc.encode(JSON.stringify({
                  error: "El servidor Python devolvió una respuesta inválida (no es JSON).",
                  diagnostic: { step: "invalid_python_json", raw_preview: full.slice(0, 300) },
                })));
              }
            }
          }
          ctrl.close();
        } catch (e) {
          try { ctrl.error(e); } catch {}
        }
      })();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no",
    },
  });
}
