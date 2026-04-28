"use client";

import { useTradingStore } from "@/store";
import { fmtUSD, pnlColor, cn } from "@/lib/utils";
import { EquityCurve } from "@/components/charts/equity-curve";
import { PnlChart } from "@/components/charts/pnl-chart";

export default function ChartPage() {
  const { backtestResult } = useTradingStore();

  if (!backtestResult) {
    return <div className="flex items-center justify-center h-64 text-text-secondary">Ejecuta un backtest primero.</div>;
  }

  const { metrics: m, trades, equity_curve } = backtestResult;

  const tradeMarkers = trades.map((t) => ({
    dir: t.direction,
    entry: t.entry_price,
    exit: t.exit_price,
    pnl: t.pnl_net,
    date: new Date(t.entry_time).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    reason: t.reason,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Price Chart</h1>
        <p className="text-sm text-text-secondary mt-0.5">Visualización de la curva de equity y trades ejecutados</p>
      </div>

      <div className="card">
        <p className="text-sm font-medium mb-3">Equity Curve — {backtestResult.period_name}</p>
        <EquityCurve data={equity_curve} initialBalance={m.initial_balance} height={320} />
      </div>

      <div className="card">
        <p className="text-sm font-medium mb-3">P&L por Trade ({trades.length} operaciones)</p>
        <PnlChart trades={trades} height={220} />
      </div>

      {/* Trade context */}
      <div className="card overflow-x-auto">
        <p className="text-sm font-medium mb-3">Contexto de Trades</p>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-text-muted">
              {["Fecha", "Dirección", "Entry", "Exit", "P&L", "Razón"].map((h) => (
                <th key={h} className="text-left py-2 pr-4 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tradeMarkers.map((t, i) => (
              <tr key={i} className="border-b border-border/40 hover:bg-bg-tertiary/50">
                <td className="py-1.5 pr-4 text-text-secondary">{t.date}</td>
                <td className="py-1.5 pr-4">
                  <span className={t.dir === "long" ? "badge-green" : "badge-red"}>{t.dir.toUpperCase()}</span>
                </td>
                <td className="py-1.5 pr-4 font-mono">{t.entry.toFixed(0)}</td>
                <td className="py-1.5 pr-4 font-mono">{t.exit.toFixed(0)}</td>
                <td className={cn("py-1.5 pr-4 font-mono font-medium", pnlColor(t.pnl))}>{fmtUSD(t.pnl)}</td>
                <td className="py-1.5 pr-4 text-text-secondary">{t.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
