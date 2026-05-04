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

  try {
    const res = await fetch(`${PYTHON_API}/backtest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    // Non-2xx from Python (e.g. 502 download error before streaming starts)
    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json({ error: text }, { status: res.status });
    }

    // The Python server streams newline keepalives then the final JSON.
    // JSON.parse ignores leading whitespace so this works transparently.
    const data = await res.json() as Record<string, unknown>;

    // Errors that occurred mid-stream are embedded in the body.
    if (data && typeof data === "object" && "error" in data) {
      const status = typeof data.__status === "number" ? data.__status : 500;
      return NextResponse.json({ error: data.error }, { status });
    }

    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: `Backend connection failed: ${String(err)}` },
      { status: 502 }
    );
  }
}
