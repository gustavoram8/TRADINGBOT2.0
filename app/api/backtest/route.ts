import { NextRequest, NextResponse } from "next/server";
import { generateMockBacktestResult } from "@/lib/mock-data";

const PYTHON_API = process.env.PYTHON_API_URL ?? "";

export async function POST(req: NextRequest) {
  const body = await req.json() as {
    start_date?: string;
    end_date?: string;
    interval?: string;
    [key: string]: unknown;
  };

  if (!PYTHON_API) {
    const startDate = body.start_date ?? "2025-10-01";
    const endDate = body.end_date ?? "2025-11-30";
    const interval = body.interval ?? "1h";
    return NextResponse.json(generateMockBacktestResult(startDate, endDate, interval));
  }

  try {
    const res = await fetch(`${PYTHON_API}/backtest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json({ error: text }, { status: res.status });
    }
    const data = await res.json() as unknown;
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 });
  }
}
