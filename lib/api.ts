import type { BacktestResult, BotConfig, ChatMessage } from "./types";

const API_BASE =
  typeof window !== "undefined" ? "" : process.env.PYTHON_API_URL ?? "";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} failed (${res.status}): ${text}`);
  }
  const data = await res.json();
  // Streaming endpoints (e.g. /backtest) embed errors in the JSON body
  // with an "error" key because HTTP status is already committed (200).
  if (data && typeof data === "object" && "error" in data) {
    const status = typeof (data as Record<string, unknown>).__status === "number"
      ? (data as Record<string, unknown>).__status
      : 500;
    throw new Error(`API ${path} failed (${status}): ${(data as Record<string, unknown>).error}`);
  }
  return data as T;
}

export async function runBacktest(
  config: BotConfig,
  startDate: string,
  endDate: string,
): Promise<BacktestResult> {
  return apiFetch<BacktestResult>("/api/backtest", {
    method: "POST",
    body: JSON.stringify({ config, start_date: startDate, end_date: endDate }),
  });
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
