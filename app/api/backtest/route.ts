import { NextRequest, NextResponse } from "next/server";
import { MOCK_BACKTEST_RESULT } from "@/lib/mock-data";

const PYTHON_API = process.env.PYTHON_API_URL ?? "";

export async function POST(req: NextRequest) {
  const body = await req.json() as unknown;

  if (!PYTHON_API) {
    return NextResponse.json(MOCK_BACKTEST_RESULT);
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
