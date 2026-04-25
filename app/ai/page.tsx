"use client";

import { useState, useRef, useEffect } from "react";
import { useTradingStore } from "@/store";
import { fmtUSD, fmtPct, cn } from "@/lib/utils";
import { Send, Trash2, Bot, User, Loader2 } from "lucide-react";
import type { ChatMessage, BacktestResult } from "@/lib/types";

const QUICK_QUESTIONS = [
  "Analiza mi rendimiento general",
  "¿Cuál es mi peor patrón de trading?",
  "¿Cómo puedo mejorar mi win rate?",
  "Evalúa mi nivel de riesgo",
];

async function callAI(
  message: string,
  history: ChatMessage[],
  context: string
): Promise<string> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, context }),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json() as { reply: string };
  return data.reply;
}

function buildContext(backtestResult: BacktestResult | null): string {
  if (!backtestResult) return "No hay datos de backtest disponibles.";
  const { metrics: m, trades, config } = backtestResult;
  return `
RESULTADOS DEL BACKTEST:
- P&L Total: ${fmtUSD(m.total_pnl)} (${fmtPct(m.total_return_pct)})
- Trades: ${m.total_trades} (${m.winning_trades}W / ${m.losing_trades}L)
- Win Rate: ${fmtPct(m.win_rate)}
- Profit Factor: ${m.profit_factor.toFixed(2)}
- Sharpe: ${m.sharpe_ratio.toFixed(2)}
- Max Drawdown: ${fmtUSD(m.max_drawdown_usd)} (${fmtPct(m.max_drawdown_pct)})
- Expectancy: ${fmtUSD(m.expectancy)}
- Avg R:R: ${m.avg_rr_ratio.toFixed(2)}:1
- Avg Win: ${fmtUSD(m.avg_win)} | Avg Loss: ${fmtUSD(-m.avg_loss)}
CONFIGURACIÓN: ${JSON.stringify(config)}
ÚLTIMOS 10 TRADES: ${JSON.stringify(trades.slice(-10).map(t => ({ dir: t.direction, pnl: t.pnl_net.toFixed(0), reason: t.reason })))}
  `.trim();
}

export default function AIPage() {
  const { backtestResult, chatHistory, addChatMessage, clearChat } = useTradingStore();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, loading]);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;
    setError("");
    const userMsg: ChatMessage = { role: "user", content: text, timestamp: new Date().toISOString() };
    addChatMessage(userMsg);
    setInput("");
    setLoading(true);
    try {
      const ctx = buildContext(backtestResult);
      const reply = await callAI(text, chatHistory, ctx);
      addChatMessage({ role: "assistant", content: reply, timestamp: new Date().toISOString() });
    } catch (e) {
      setError(String(e));
      addChatMessage({
        role: "assistant",
        content: "No pude conectar con el backend de IA. Verifica que `GEMINI_API_KEY` esté configurado en Vercel.",
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">AI Analyst</h1>
          <p className="text-sm text-text-secondary mt-0.5">Análisis cuantitativo con Gemini · Contexto ICT</p>
        </div>
        <button onClick={clearChat} className="btn-secondary flex items-center gap-1.5">
          <Trash2 size={13} /> Limpiar chat
        </button>
      </div>

      {/* Quick questions */}
      <div className="flex flex-wrap gap-2">
        {QUICK_QUESTIONS.map((q) => (
          <button key={q} onClick={() => sendMessage(q)} className="text-xs px-3 py-1.5 bg-bg-secondary border border-border rounded-full hover:border-brand-blue hover:text-brand-blue transition-colors">
            {q}
          </button>
        ))}
      </div>

      {/* Chat window */}
      <div className="flex-1 overflow-y-auto space-y-4 card">
        {chatHistory.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center py-12">
            <div className="w-12 h-12 rounded-full bg-brand-dark/20 flex items-center justify-center">
              <Bot size={24} className="text-brand-blue" />
            </div>
            <p className="text-text-secondary text-sm">
              Hola, soy Chuky AI. Pregúntame sobre tu estrategia ICT, resultados o gestión de riesgo.
            </p>
          </div>
        )}

        {chatHistory.map((msg, i) => (
          <div key={i} className={cn("flex gap-3", msg.role === "user" ? "flex-row-reverse" : "flex-row")}>
            <div className={cn(
              "flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center",
              msg.role === "user" ? "bg-brand-dark/30" : "bg-fin-blue/20"
            )}>
              {msg.role === "user" ? <User size={14} className="text-brand-blue" /> : <Bot size={14} className="text-fin-blue" />}
            </div>
            <div className={cn(
              "max-w-[80%] px-4 py-3 rounded-lg text-sm leading-relaxed whitespace-pre-wrap",
              msg.role === "user"
                ? "bg-brand-dark/20 text-text-primary"
                : "bg-bg-tertiary text-text-primary border border-border"
            )}>
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-fin-blue/20 flex items-center justify-center flex-shrink-0">
              <Bot size={14} className="text-fin-blue" />
            </div>
            <div className="bg-bg-tertiary border border-border rounded-lg px-4 py-3 flex items-center gap-2">
              <Loader2 size={14} className="animate-spin text-brand-blue" />
              <span className="text-sm text-text-secondary">Analizando...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && <p className="text-xs text-fin-red">{error}</p>}

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage(input)}
          placeholder="Pregunta sobre tu estrategia, riesgo o resultados..."
          className="flex-1 bg-bg-secondary border border-border rounded-md px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-brand-blue"
        />
        <button onClick={() => sendMessage(input)} disabled={!input.trim() || loading} className="btn-primary px-4">
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
