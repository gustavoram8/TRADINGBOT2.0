import type { BacktestResult, BotConfig, ChatMessage } from "./types";

const API_BASE =
  typeof window !== "undefined" ? "" : process.env.PYTHON_API_URL ?? "";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (networkErr) {
    // Network-level failure (server down, CORS, DNS, etc.)
    const hint =
      typeof window !== "undefined"
        ? `No se pudo conectar con el servidor Next.js en ${window.location.origin}. Ruta: ${url}`
        : `fetch() falló en el servidor para ${url}`;
    throw new Error(`[RED] ${hint} — ${String(networkErr)}`);
  }
  if (!res.ok) {
    let text = "";
    try { text = await res.text(); } catch { /* ignore */ }
    throw new Error(`[HTTP ${res.status}] ${path} — ${text || res.statusText}`);
  }
  let data: unknown;
  try {
    data = await res.json();
  } catch (parseErr) {
    // TypeError / "Failed to fetch" here means the response stream was cut
    // (connection dropped by nginx/proxy), not a malformed JSON payload.
    const errStr = String(parseErr);
    const isNetworkAbort =
      parseErr instanceof TypeError ||
      errStr.includes("Failed to fetch") ||
      errStr.includes("NetworkError") ||
      errStr.includes("network error");
    if (isNetworkAbort) {
      const hint =
        typeof window !== "undefined"
          ? `La conexión fue cortada mientras se recibía la respuesta de ${window.location.origin}. Ruta: ${path}`
          : `Stream cortado para ${path}`;
      throw new Error(`[RED] ${hint} — ${errStr}`);
    }
    throw new Error(`[PARSE] Respuesta no es JSON válido desde ${path} — ${errStr}`);
  }
  // Streaming endpoints embed errors in the JSON body (HTTP 200 already committed)
  if (data && typeof data === "object" && "error" in data) {
    const d = data as Record<string, unknown>;
    const status = typeof d.__status === "number" ? d.__status : 500;
    throw new Error(`[BACKEND ${status}] ${path} — ${d.error}`);
  }
  return data as T;
}

export async function runBacktest(
  config: BotConfig,
  startDate: string,
  endDate: string,
): Promise<BacktestResult> {
  // POST starts the job immediately and returns a jobId.
  // This avoids long-lived HTTP connections that routers/firewalls close.
  const { jobId } = await apiFetch<{ jobId: string }>("/api/backtest", {
    method: "POST",
    body: JSON.stringify({ config, start_date: startDate, end_date: endDate }),
  });

  // Poll every 2 s until the job completes (max 15 min).
  const deadline = Date.now() + 15 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 2000));
    const poll = await apiFetch<BacktestResult | { status: "running" }>(
      `/api/backtest?jobId=${encodeURIComponent(jobId)}`
    );
    if ("status" in poll && poll.status === "running") continue;
    return poll as BacktestResult;
  }
  throw new Error("[RED] El backtest superó 15 minutos sin respuesta.");
}

export async function fetchConfigs(): Promise<BotConfig[]> {
  return apiFetch<BotConfig[]>("/api/configs");
}

export async function saveConfig(config: BotConfig): Promise<void> {
  await apiFetch("/api/configs", {
    method: "POST",
    body: JSON.stringify(config),
  });
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[],
  context?: BacktestResult
): Promise<string> {
  const res = await apiFetch<{ reply: string }>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, history, context }),
  });
  return res.reply;
}
