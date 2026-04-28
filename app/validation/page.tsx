"use client";

import { useState } from "react";
import { useTradingStore } from "@/store";
import { fmtUSD, fmtPct, cn } from "@/lib/utils";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  Cell, ReferenceLine, ResponsiveContainer,
} from "recharts";
import type { GoNoGoCheck } from "@/lib/types";
import { CheckCircle2, XCircle, AlertCircle, Play } from "lucide-react";

function runMonteCarlo(pnls: number[], iterations = 1000) {
  const results: number[] = [];
  const maxDDs: number[] = [];
  for (let i = 0; i < iterations; i++) {
    let equity = 0;
    let peak = 0;
    let maxDD = 0;
    for (let j = 0; j < pnls.length; j++) {
      const pnl = pnls[Math.floor(Math.random() * pnls.length)];
      equity += pnl;
      peak = Math.max(peak, equity);
      maxDD = Math.max(maxDD, peak - equity);
    }
    results.push(equity);
    maxDDs.push(maxDD);
  }
  results.sort((a, b) => a - b);
  maxDDs.sort((a, b) => a - b);
  const probProfit = results.filter((r) => r > 0).length / iterations;
  const maxDDP95 = maxDDs[Math.floor(iterations * 0.95)];
  const finalPnlP50 = results[Math.floor(iterations * 0.5)];
  const probExceedDD = maxDDs.filter((d) => d > 2500).length / iterations;
  return { probProfit, maxDDP95, finalPnlP50, probExceedDD, results, maxDDs };
}

export default function ValidationPage() {
  const { backtestResult } = useTradingStore();
  const m = backtestResult?.metrics;
  const trades = backtestResult?.trades ?? [];
  const [activeTab, setActiveTab] = useState<"mc" | "consistency" | "gonogo">("gonogo");
  const [mcResult, setMcResult] = useState<ReturnType<typeof runMonteCarlo> | null>(null);
  const [consistencyResult, setConsistencyResult] = useState<{
    passed: boolean; ratio: number; top3: number; totalPos: number;
  } | null>(null);

  if (!m) return <div className="flex items-center justify-center h-64 text-text-secondary">Ejecuta un backtest primero.</div>;

  function handleMC() {
    const pnls = trades.map((t) => t.pnl_net);
    setMcResult(runMonteCarlo(pnls));
  }

  function handleConsistency() {
    const daily = new Map<string, number>();
    for (const t of trades) {
      const d = t.entry_time.slice(0, 10);
      daily.set(d, (daily.get(d) ?? 0) + t.pnl_net);
    }
    const vals = Array.from(daily.values()).sort((a, b) => b - a);
    const totalPos = vals.filter((v) => v > 0).reduce((s, v) => s + v, 0);
    const top3 = vals.slice(0, 3).filter((v) => v > 0).reduce((s, v) => s + v, 0);
    const ratio = totalPos > 0 ? top3 / totalPos : 0;
    setConsistencyResult({ passed: ratio < 0.8, ratio, top3, totalPos });
  }

  const checks: GoNoGoCheck[] = [
    { label: "Sharpe Ratio > 0.5", passed: m.sharpe_ratio > 0.5, value: m.sharpe_ratio.toFixed(2), threshold: "≥ 0.5" },
    { label: "Profit Factor > 1.0", passed: m.profit_factor > 1.0, value: m.profit_factor.toFixed(2), threshold: "≥ 1.0" },
    { label: "Win Rate > 40%", passed: m.win_rate > 0.4, value: fmtPct(m.win_rate), threshold: "≥ 40%" },
    { label: "Max Drawdown < $2,500", passed: m.max_drawdown_usd < 2500, value: fmtUSD(m.max_drawdown_usd), threshold: "< $2,500" },
    { label: "Total Trades ≥ 10", passed: m.total_trades >= 10, value: String(m.total_trades), threshold: "≥ 10" },
    { label: "Expectancy > $0", passed: m.expectancy > 0, value: fmtUSD(m.expectancy), threshold: "> $0" },
  ];
  const passed = checks.filter((c) => c.passed).length;
  const goNoGo = passed === checks.length ? "GO" : passed >= checks.length * 0.8 ? "CAUTION" : "NO-GO";

  const histBuckets = (data: number[], buckets = 30) => {
    if (!data.length) return [];
    const min = Math.min(...data), max = Math.max(...data);
    const step = (max - min) / buckets;
    return Array.from({ length: buckets }, (_, i) => {
      const lo = min + i * step;
      const hi = lo + step;
      return { range: `$${lo.toFixed(0)}`, count: data.filter((v) => v >= lo && v < hi).length };
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Validation</h1>
        <p className="text-sm text-text-secondary mt-0.5">Validación científica de la estrategia</p>
      </div>

      <div className="border-b border-border flex gap-1">
        {([["gonogo", "GO / NO-GO"], ["mc", "Monte Carlo"], ["consistency", "Consistencia"]] as const).map(([t, l]) => (
          <button key={t} onClick={() => setActiveTab(t)} className={cn("px-4 py-2 text-sm", activeTab === t ? "tab-active" : "tab-inactive")}>
            {l}
          </button>
        ))}
      </div>

      {activeTab === "gonogo" && (
        <div className="space-y-4">
          <div className={cn(
            "card flex items-center gap-4",
            goNoGo === "GO" ? "border-fin-green/30" : goNoGo === "CAUTION" ? "border-fin-gold/30" : "border-fin-red/30"
          )}>
            {goNoGo === "GO" ? <CheckCircle2 size={32} className="text-fin-green" /> : goNoGo === "CAUTION" ? <AlertCircle size={32} className="text-fin-gold" /> : <XCircle size={32} className="text-fin-red" />}
            <div>
              <p className={cn("text-2xl font-bold", goNoGo === "GO" ? "text-fin-green" : goNoGo === "CAUTION" ? "text-fin-gold" : "text-fin-red")}>
                {goNoGo}
              </p>
              <p className="text-sm text-text-secondary">{passed} de {checks.length} criterios cumplidos</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {checks.map((c) => (
              <div key={c.label} className={cn("card-sm flex items-center gap-3 border", c.passed ? "border-fin-green/20" : "border-fin-red/20")}>
                {c.passed ? <CheckCircle2 size={16} className="text-fin-green flex-shrink-0" /> : <XCircle size={16} className="text-fin-red flex-shrink-0" />}
                <div className="flex-1">
                  <p className="text-sm font-medium">{c.label}</p>
                  <p className="text-xs text-text-secondary">Valor: <span className="font-mono text-text-primary">{c.value}</span> · Meta: {c.threshold}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "mc" && (
        <div className="space-y-4">
          <button onClick={handleMC} className="btn-primary flex items-center gap-2">
            <Play size={14} /> Ejecutar Monte Carlo (1,000 iteraciones)
          </button>
          {mcResult && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { l: "Prob. Rentable", v: fmtPct(mcResult.probProfit), pos: mcResult.probProfit > 0.5 },
                  { l: "DD P95", v: fmtUSD(mcResult.maxDDP95), pos: mcResult.maxDDP95 < 2500 },
                  { l: "P&L Mediano", v: fmtUSD(mcResult.finalPnlP50), pos: mcResult.finalPnlP50 > 0 },
                  { l: "Prob. Exceder DD", v: fmtPct(mcResult.probExceedDD), pos: mcResult.probExceedDD < 0.2 },
                ].map(({ l, v, pos }) => (
                  <div key={l} className="kpi-card">
                    <p className="text-xs text-text-secondary">{l}</p>
                    <p className={cn("text-xl font-bold font-mono mt-1", pos ? "text-fin-green" : "text-fin-red")}>{v}</p>
                  </div>
                ))}
              </div>
              <div className="card">
                <p className="text-sm font-medium mb-3">Distribución P&L Final (1,000 sims)</p>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={histBuckets(mcResult.results)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1C2333" vertical={false} />
                    <XAxis dataKey="range" tick={{ fill: "#8B949E", fontSize: 9 }} tickLine={false} axisLine={false} interval={4} />
                    <YAxis tick={{ fill: "#8B949E", fontSize: 10 }} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ background: "#1C2333", border: "1px solid #30363D", borderRadius: 6, fontSize: 12 }} />
                    <ReferenceLine x={`$0`} stroke="#30363D" strokeDasharray="4 4" />
                    <Bar dataKey="count" fill="#42A5F5" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>
      )}

      {activeTab === "consistency" && (
        <div className="space-y-4">
          <button onClick={handleConsistency} className="btn-primary flex items-center gap-2">
            <Play size={14} /> Verificar Consistencia (Regla OneUpTrader)
          </button>
          <div className="card text-sm text-text-secondary">
            <p>Regla OneUpTrader: la suma de los 3 mejores días no debe superar el 80% del P&L positivo total. Si lo supera, los beneficios pueden ser retenidos.</p>
          </div>
          {consistencyResult && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className={cn("card border-2", consistencyResult.passed ? "border-fin-green/40" : "border-fin-red/40")}>
                <div className="flex items-center gap-3">
                  {consistencyResult.passed ? <CheckCircle2 size={28} className="text-fin-green" /> : <XCircle size={28} className="text-fin-red" />}
                  <div>
                    <p className={cn("text-xl font-bold", consistencyResult.passed ? "text-fin-green" : "text-fin-red")}>
                      {consistencyResult.passed ? "PASS" : "FAIL"}
                    </p>
                    <p className="text-xs text-text-secondary">Regla de consistencia</p>
                  </div>
                </div>
                <div className="mt-4 space-y-2 text-sm">
                  {[
                    ["Top 3 días", fmtUSD(consistencyResult.top3)],
                    ["Total positivo", fmtUSD(consistencyResult.totalPos)],
                    ["Ratio", fmtPct(consistencyResult.ratio)],
                    ["Límite", "< 80%"],
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-text-secondary">{k}</span>
                      <span className="font-mono">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
