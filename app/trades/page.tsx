"use client";

import { useState, useMemo } from "react";
import { useTradingStore } from "@/store";
import { fmtUSD, fmtPct, pnlColor, cn } from "@/lib/utils";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  Cell, ResponsiveContainer, Legend,
} from "recharts";

export default function TradesPage() {
  const { backtestResult } = useTradingStore();
  const trades = backtestResult?.trades ?? [];

  const [direction, setDirection] = useState<"all" | "long" | "short">("all");
  const [result, setResult] = useState<"all" | "win" | "loss">("all");

  const filtered = useMemo(
    () =>
      trades.filter((t) => {
        if (direction !== "all" && t.direction !== direction) return false;
        if (result === "win" && t.pnl_net <= 0) return false;
        if (result === "loss" && t.pnl_net > 0) return false;
        return true;
      }),
    [trades, direction, result]
  );

  const totalPnl = filtered.reduce((s, t) => s + t.pnl_net, 0);
  const wins = filtered.filter((t) => t.pnl_net > 0);
  const winRate = filtered.length > 0 ? wins.length / filtered.length : 0;

  // Daily P&L
  const dailyMap = new Map<string, { pnl: number; count: number; wins: number }>();
  for (const t of filtered) {
    const date = t.entry_time.slice(0, 10);
    const cur = dailyMap.get(date) ?? { pnl: 0, count: 0, wins: 0 };
    dailyMap.set(date, {
      pnl: cur.pnl + t.pnl_net,
      count: cur.count + 1,
      wins: cur.wins + (t.pnl_net > 0 ? 1 : 0),
    });
  }
  const dailyData = Array.from(dailyMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([date, v]) => ({ date: date.slice(5), pnl: Math.round(v.pnl), count: v.count }));

  // Hourly
  const hourlyMap = new Map<number, { pnl: number; count: number; wins: number }>();
  for (const t of filtered) {
    const h = new Date(t.entry_time).getHours();
    const cur = hourlyMap.get(h) ?? { pnl: 0, count: 0, wins: 0 };
    hourlyMap.set(h, {
      pnl: cur.pnl + t.pnl_net,
      count: cur.count + 1,
      wins: cur.wins + (t.pnl_net > 0 ? 1 : 0),
    });
  }
  const hourlyData = Array.from(hourlyMap.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([h, v]) => ({ hour: `${h}:00`, pnl: Math.round(v.pnl), count: v.count }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Trade Explorer</h1>
        <p className="text-sm text-text-secondary mt-0.5">Análisis detallado de todas las operaciones</p>
      </div>

      {/* Filters */}
      <div className="card flex flex-wrap gap-4 items-center">
        <div className="flex gap-1">
          {(["all", "long", "short"] as const).map((d) => (
            <button
              key={d}
              onClick={() => setDirection(d)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                direction === d
                  ? d === "all" ? "bg-brand-dark text-white" : d === "long" ? "bg-fin-green/20 text-fin-green" : "bg-fin-red/20 text-fin-red"
                  : "bg-bg-tertiary text-text-secondary hover:text-text-primary"
              )}
            >
              {d === "all" ? "Todos" : d.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {(["all", "win", "loss"] as const).map((r) => (
            <button
              key={r}
              onClick={() => setResult(r)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                result === r ? "bg-brand-dark text-white" : "bg-bg-tertiary text-text-secondary hover:text-text-primary"
              )}
            >
              {r === "all" ? "Todos" : r === "win" ? "Ganadores" : "Perdedores"}
            </button>
          ))}
        </div>
        <div className="ml-auto flex gap-4 text-sm">
          <span className="text-text-secondary">{filtered.length} trades</span>
          <span className={pnlColor(totalPnl) + " font-mono font-medium"}>{fmtUSD(totalPnl)}</span>
          <span className="text-fin-blue font-mono">{fmtPct(winRate)} WR</span>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <p className="text-sm font-medium mb-3">P&L Diario</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1C2333" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: "#8B949E", fontSize: 9 }} tickLine={false} axisLine={false} interval={3} />
              <YAxis tick={{ fill: "#8B949E", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
              <Tooltip
                formatter={(v: number) => [`$${v}`, "P&L"]}
                contentStyle={{ background: "#1C2333", border: "1px solid #30363D", borderRadius: 6, fontSize: 12 }}
              />
              <Bar dataKey="pnl" radius={[2, 2, 0, 0]}>
                {dailyData.map((d, i) => (
                  <Cell key={i} fill={d.pnl >= 0 ? "#00C853" : "#EF5350"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <p className="text-sm font-medium mb-3">P&L por Hora (ET)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1C2333" vertical={false} />
              <XAxis dataKey="hour" tick={{ fill: "#8B949E", fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: "#8B949E", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
              <Tooltip
                formatter={(v: number) => [`$${v}`, "P&L"]}
                contentStyle={{ background: "#1C2333", border: "1px solid #30363D", borderRadius: 6, fontSize: 12 }}
              />
              <Bar dataKey="pnl" radius={[2, 2, 0, 0]}>
                {hourlyData.map((d, i) => (
                  <Cell key={i} fill={d.pnl >= 0 ? "#00C853" : "#EF5350"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-x-auto">
        <p className="text-sm font-medium mb-3">Todos los Trades ({filtered.length})</p>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-muted border-b border-border">
              {["#", "Entrada", "Salida", "Dir", "Price In", "Price Out", "SL", "TP", "Contr.", "P&L Neto", "Max Fav %TP", "Razón", "Revisar"].map((h) => (
                <th key={h} className="text-left py-2 pr-3 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((t, i) => (
              <tr key={i} className="border-b border-border/40 hover:bg-bg-tertiary/50">
                <td className="py-1.5 pr-3 text-text-muted">{i + 1}</td>
                <td className="py-1.5 pr-3 text-text-secondary">
                  {new Date(t.entry_time).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                </td>
                <td className="py-1.5 pr-3 text-text-secondary">
                  {new Date(t.exit_time).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                </td>
                <td className="py-1.5 pr-3">
                  <span className={t.direction === "long" ? "badge-green" : "badge-red"}>{t.direction.toUpperCase()}</span>
                </td>
                <td className="py-1.5 pr-3 font-mono">{t.entry_price.toFixed(0)}</td>
                <td className="py-1.5 pr-3 font-mono">{t.exit_price.toFixed(0)}</td>
                <td className="py-1.5 pr-3 font-mono text-text-secondary">{t.sl_price.toFixed(0)}</td>
                <td className="py-1.5 pr-3 font-mono text-text-secondary">{t.tp_price.toFixed(0)}</td>
                <td className="py-1.5 pr-3 text-center">{t.contracts}</td>
                <td className={cn("py-1.5 pr-3 font-mono font-medium", pnlColor(t.pnl_net))}>{fmtUSD(t.pnl_net)}</td>
                <td className="py-1.5 pr-3 font-mono text-text-secondary">
                  {t.max_favorable_pct_of_tp != null
                    ? `${(t.max_favorable_pct_of_tp * 100).toFixed(0)}%`
                    : "—"}
                </td>
                <td className="py-1.5 pr-3 text-text-secondary">{t.reason}</td>
                <td className="py-1.5 pr-3">
                  {t.needs_review ? (
                    <span
                      className="badge-red"
                      title="Trade no alcanzó 60% del TP — lectura potencialmente errónea"
                    >
                      ⚠ Revisar
                    </span>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
