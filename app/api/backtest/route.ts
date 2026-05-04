import { NextRequest, NextResponse } from "next/server";
import { generateMockBacktestResult, DEFAULT_CONFIG } from "@/lib/mock-data";
import type { BotConfig } from "@/lib/types";

const PYTHON_API = process.env.PYTHON_API_URL ?? "";

// In-process job store. Works for single-instance deployments (PM2 fork mode).
// Keys are jobIds; values hold the job state.
type JobState =
  | { status: "running" }
  | { status: "done"; result: unknown }
  | { status: "error"; error: string };

const jobs = new Map<string, JobState>();

// Clean up jobs older than 30 min to avoid memory leaks.
setInterval(() => {
  const cutoff = Date.now() - 30 * 60 * 1000;
  for (const [id] of jobs) {
    const ts = Number(id.split("-")[1] ?? 0);
    if (ts < cutoff) jobs.delete(id);
  }
}, 5 * 60 * 1000);

// POST /api/backtest — start a job, return jobId immediately.
export async function POST(req: NextRequest) {
  const body = await req.json() as {
    start_date?: string;
    end_date?: string;
    interval?: string;
    config?: BotConfig;
    [key: string]: unknown;
  };

  // Mock mode — no Python backend configured.
  if (!PYTHON_API) {
    const startDate = body.start_date ?? "2025-10-01";
    const endDate   = body.end_date   ?? "2025-11-30";
    const interval  = body.interval   ?? "1h";
    const config    = body.config     ?? DEFAULT_CONFIG;
    const result = generateMockBacktestResult(startDate, endDate, interval, config);
    const jobId = `mock-${Date.now()}`;
    jobs.set(jobId, { status: "done", result });
    return NextResponse.json({ jobId }, { status: 202 });
  }

  const jobId = `bt-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  jobs.set(jobId, { status: "running" });

  const backendUrl = `${PYTHON_API}/backtest`;

  // Run the Python fetch in the background — no long-lived HTTP connection
  // to the browser needed. The browser polls GET /api/backtest?jobId=... .
  void (async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15 * 60 * 1000); // 15 min
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
        jobs.set(jobId, {
          status: "error",
          error: `El servidor Python respondió con error HTTP ${res.status}: ${text || res.statusText}`,
        });
        return;
      }

      // Python streams keepalive \n bytes then the final JSON.
      // res.text() buffers all of it; JSON.parse ignores leading whitespace.
      const raw = await res.text();
      // Find the first '{' to skip leading newlines from Python keepalives.
      const jsonStart = raw.indexOf("{");
      const jsonText = jsonStart >= 0 ? raw.slice(jsonStart) : raw;
      const result = JSON.parse(jsonText);

      if (result && typeof result === "object" && "error" in result) {
        jobs.set(jobId, { status: "error", error: String(result.error) });
      } else {
        jobs.set(jobId, { status: "done", result });
      }
    } catch (err) {
      clearTimeout(timeoutId);
      const isAbort = err instanceof Error && err.name === "AbortError";
      jobs.set(jobId, {
        status: "error",
        error: isAbort
          ? "El backtest superó el tiempo máximo (15 min) sin respuesta del servidor Python."
          : `No se pudo conectar con el servidor Python en ${backendUrl}: ${String(err)}`,
      });
    }
  })();

  return NextResponse.json({ jobId }, { status: 202 });
}

// GET /api/backtest?jobId=... — poll for job result.
export async function GET(req: NextRequest) {
  const jobId = req.nextUrl.searchParams.get("jobId");
  if (!jobId) {
    return NextResponse.json({ error: "Falta el parámetro jobId" }, { status: 400 });
  }

  const job = jobs.get(jobId);
  if (!job) {
    return NextResponse.json({ error: "Job no encontrado o expirado" }, { status: 404 });
  }

  if (job.status === "running") {
    return NextResponse.json({ status: "running" });
  }

  jobs.delete(jobId);

  if (job.status === "error") {
    return NextResponse.json({ error: job.error }, { status: 500 });
  }

  return NextResponse.json(job.result);
}
