"use client";

import { useTradingStore } from "@/store";
import { fmtUSD, fmtPct, pnlColor, cn } from "@/lib/utils";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, BarChart, Bar, Cell } from "recharts";
import { AlertTriangle, ShieldCheck, ShieldAlert, ShieldOff } from "lucide-react";

const DD_LIMIT = 2500;

export default function RiskPage() {
  const { backtestResult } = useTradingStore();
  const m = backtestResult?.metrics;
  const curve = backtestResult?.equity_curve ?? [];
  const trades = backtestResult?.trades ?? [];
  const config = backtestResult?.config;

  if (!m) return <div className="flex items-center justify-center h-64 text-text-secondary">Ejecuta un backtest primero.</div>;

  const ddPct = m.max_drawdown_usd / DD_LIMIT;
  const ddColor = ddPct >= 0.96 ? "#EF5350" : ddPct >= 0.8 ? "#FFD54F" : "#00C853";

  const ddData = curve.map((p) => ({
    date: new Date(p.datetime).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    drawdown: Math.round(p.drawdown),
  }));

  const pnlSeq = trades.map((t, i) => ({ n: `#${i + 1}`, pnl: Math.round(t.pnl_net) }));

  // Streak analysis
  let maxWinStreak = 0, maxLossStreak = 0, cur = 0;
  for (const t of trades) {
    if (t.pnl_net > 0) {
      cur = cur > 0 ? cur + 1 : 1;
      maxWinStreak = Math.max(maxWinStreak, cur);
    } else {
      cur = cur < 0 ? cur - 1 : -1;
      maxLossStreak = Math.max(maxLossStreak, Math.abs(cur));
    }
  }

  const killSwitches = [
    {
      label: "Nivel 1 — Reducir contratos",
      desc: `DD > $${config ? (DD_LIMIT * 0.8).toFixed(0) : "2,000"}`,
      triggered: m.max_drawdown_usd > DD_LIMIT * 0.8,
      icon: ShieldAlert,
    },
    {
      label: "Nivel 2 — Stop día",
      desc: `Pérdida diaria > $${config?.max_daily_loss ?? 550}`,
      triggered: m.worst_day_pnl < -(config?.max_daily_loss ?? 550),
      icon: ShieldOff,
    },
    {
      label: "Nivel 3 — Stop total",
      desc: `DD > $${DD_LIMIT * 0.96}`,
      triggered: m.max_drawdown_usd > DD_LIMIT * 0.96,
      icon: AlertTriangle,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Risk Center</h1>
        <p className="text-sm text-text-secondary mt-0.5">Control de riesgo y kill-switches del trailing drawdown</p>
      </div>

      {/* Drawdown gauge */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card md:col-span-1">
          <p className="text-sm font-medium mb-4">Trailing Drawdown</p>
          <div className="flex flex-col items-center gap-3">
            <div
              className="relative w-36 h-36 rounded-full flex items-center justify-center"
              style={{
                background: `conic-gradient(${ddColor} ${ddPct * 360}deg, #1C2333 0deg)`,
              }}
            >
              <div className="w-24 h-24 rounded-full bg-bg-secondary flex flex-col items-center justify-center">
                <p className="text-xl font-bold font-mono" style={{ color: ddColor }}>
                  {fmtPct(ddPct, 0)}
                </p>
                <p className="text-[10px] text-text-muted">usado</p>
              </div>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold font-mono" style={{ color: ddColor }}>
                {fmtUSD(m.max_drawdown_usd)}
              </p>
              <p className="text-xs text-text-secondary">de {fmtUSD(DD_LIMIT)} límite</p>
            </div>
          </div>
        </div>

        <div className="card md:col-span-2">
          <p className="text-sm font-medium mb-3">Kill-Switches</p>
          <div className="space-y-3">
            {killSwitches.map(({ label, desc, triggered, icon: Icon }) => (
              <div
                key={label}
                className={cn(
                  "flex items-center gap-3 p-3 rounded-md border",
                  triggered
                    ? "border-fin-red/40 bg-fin-red/5"
                    : "border-fin-green/40 bg-fin-green/5"
                )}
              >
                <Icon size={16} className={triggered ? "text-fin-red" : "text-fin-green"} />
                <div className="flex-1">
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-text-secondary">{desc}</p>
                </div>
                <span className={triggered ? "badge-red" : "badge-green"}>
                  {triggered ? "ACTIVO" : "OK"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Underwater drawdown chart */}
      <div className="card">
        <p className="text-sm font-medium mb-3">Evolución del Drawdown</p>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={ddData}>
            <defs>
              <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#EF5350" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#EF5350" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1C2333" />
            <XAxis dataKey="date" tick={{ fill: "#8B949E", fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill: "#8B949E", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
            <Tooltip
              formatter={(v: number) => [`$${v}`, "Drawdown"]}
              contentStyle={{ background: "#1C2333", border: "1px solid #30363D", borderRadius: 6, fontSize: 12 }}
            />
            <ReferenceLine y={2000} stroke="#FFD54F" strokeDasharray="4 4" label={{ value: "Nivel 1", fill: "#FFD54F", fontSize: 10 }} />
            <ReferenceLine y={2400} stroke="#EF5350" strokeDasharray="4 4" label={{ value: "Stop Total", fill: "#EF5350", fontSize: 10 }} />
            <Area type="monotone" dataKey="drawdown" stroke="#EF5350" strokeWidth={2} fill="url(#ddGrad)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Sequential P&L + Streaks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card lg:col-span-2">
          <p className="text-sm font-medium mb-3">P&L Secuencial por Trade</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={pnlSeq}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1C2333" vertical={false} />
              <XAxis dataKey="n" tick={{ fill: "#8B949E", fontSize: 9 }} tickLine={false} axisLine={false} interval={4} />
              <YAxis tick={{ fill: "#8B949E", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
              <Tooltip formatter={(v: number) => [`$${v}`, "P&L"]} contentStyle={{ background: "#1C2333", border: "1px solid #30363D", borderRadius: 6, fontSize: 12 }} />
              <ReferenceLine y={0} stroke="#30363D" />
              <Bar dataKey="pnl" radius={[2, 2, 0, 0]}>
                {pnlSeq.map((d, i) => <Cell key={i} fill={d.pnl >= 0 ? "#00C853" : "#EF5350"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <p className="text-sm font-medium mb-4">Análisis de Rachas</p>
          <div className="space-y-4">
            <div className="bg-bg-tertiary rounded-md p-3">
              <p className="text-xs text-text-secondary">Máx. racha ganadora</p>
              <p className="text-2xl font-bold text-fin-green mt-1">{maxWinStreak} trades</p>
            </div>
            <div className="bg-bg-tertiary rounded-md p-3">
              <p className="text-xs text-text-secondary">Máx. racha perdedora</p>
              <p className="text-2xl font-bold text-fin-red mt-1">{maxLossStreak} trades</p>
            </div>
            <div className="bg-bg-tertiary rounded-md p-3">
              <p className="text-xs text-text-secondary">Mejor día</p>
              <p className="text-lg font-bold text-fin-green font-mono">{fmtUSD(m.best_day_pnl)}</p>
            </div>
            <div className="bg-bg-tertiary rounded-md p-3">
              <p className="text-xs text-text-secondary">Peor día</p>
              <p className="text-lg font-bold text-fin-red font-mono">{fmtUSD(m.worst_day_pnl)}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
