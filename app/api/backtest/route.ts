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
  try {
    const res = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

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

    // Pass Python's streaming body through directly so nginx sees the
    // keepalive newlines and resets its proxy_read_timeout on each chunk.
    return new Response(res.body, {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    const isNetworkError =
      err instanceof TypeError && String(err).includes("fetch");
    return NextResponse.json(
      {
        error: isNetworkError
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
      { status: 502 }
    );
  }
}
