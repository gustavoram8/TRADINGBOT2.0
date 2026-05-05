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
  // Generous timeout: backtests can take 2–5 min for large date ranges.
  // Python sends keepalive "\n" bytes every 5s so the TCP connection stays
  // alive; we just need Node.js not to abort before the final JSON arrives.
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

    // Buffer the full Python response (which includes keepalive "\n" bytes
    // before the final JSON). This prevents the browser from receiving a
    // partial/aborted stream and throwing "TypeError: Failed to fetch".
    // nginx proxy_read_timeout is set to 600s, so buffering is safe.
    const rawText = await res.text();
    const trimmed = rawText.trim();

    if (!trimmed) {
      return NextResponse.json(
        {
          error: "El servidor Python cerró la conexión sin devolver datos. El backtest puede haber fallado internamente.",
          diagnostic: {
            step: "empty_python_response",
            backend_url: backendUrl,
            raw_length: rawText.length,
          },
        },
        { status: 502 }
      );
    }

    // Validate JSON before forwarding — surface Python serialization errors
    // as a readable 502 instead of a cryptic [PARSE] browser error.
    try {
      JSON.parse(trimmed);
    } catch {
      return NextResponse.json(
        {
          error: `El servidor Python devolvió una respuesta inválida (no es JSON).`,
          diagnostic: {
            step: "invalid_python_json",
            backend_url: backendUrl,
            raw_preview: trimmed.slice(0, 300),
          },
        },
        { status: 502 }
      );
    }

    return new Response(trimmed, {
      headers: { "Content-Type": "application/json" },
    });
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
