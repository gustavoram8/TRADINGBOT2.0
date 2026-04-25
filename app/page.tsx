"use client";

import { useTradingStore } from "@/store";
import { EquityCurve } from "@/components/charts/equity-curve";
import { PnlChart } from "@/components/charts/pnl-chart";
import { fmtUSD, fmtPct, pnlColor, cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Activity, AlertTriangle, Target, BarChart2 } from "lucide-react";

function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  color = "text-text-primary",
}: {
  label: string;
  value: string;
  sub?: string;
  icon?: React.ElementType;
  color?: string;
}) {
  return (
    <div className="kpi-card">
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-secondary">{label}</span>
        {Icon && <Icon size={14} className="text-text-muted" />}
      </div>
      <p className={cn("text-2xl font-bold font-mono mt-1", color)}>{value}</p>
      {sub && <p className="text-xs text-text-muted">{sub}</p>}
    </div>
  );
}

export default function OverviewPage() {
  const { backtestResult } = useTradingStore();

  if (!backtestResult) {
    return (
      <div className="flex items-center justify-center h-64 text-text-secondary">
        No hay datos. Ejecuta un backtest primero.
      </div>
    );
  }

  const { metrics, trades, equity_curve, config, period_name } = backtestResult;
  const recent = trades.slice(-10).reverse();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Overview</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            {period_name ?? "Backtest"} · {config.name} · MNQ / NAS100
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn("badge-green", metrics.total_pnl < 0 && "badge-red")}>
            {metrics.total_pnl >= 0 ? "PROFITABLE" : "LOSS"}
          </span>
          {metrics.consistency_check_passed && (
            <span className="badge-blue">CONSISTENCY ✓</span>
          )}
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KpiCard
          label="Total P&L"
          value={fmtUSD(metrics.total_pnl)}
          sub={fmtPct(metrics.total_return_pct) + " return"}
          icon={TrendingUp}
          color={pnlColor(metrics.total_pnl)}
        />
        <KpiCard
          label="Win Rate"
          value={fmtPct(metrics.win_rate)}
          sub={`${metrics.winning_trades}W / ${metrics.losing_trades}L`}
          icon={Target}
          color="text-fin-blue"
        />
        <KpiCard
          label="Profit Factor"
          value={metrics.profit_factor.toFixed(2)}
          sub="bruto / pérdidas"
          icon={BarChart2}
          color={metrics.profit_factor >= 1.5 ? "text-fin-green" : metrics.profit_factor >= 1 ? "text-fin-gold" : "text-fin-red"}
        />
        <KpiCard
          label="Sharpe Ratio"
          value={metrics.sharpe_ratio.toFixed(2)}
          sub="anualizado"
          icon={Activity}
          color={metrics.sharpe_ratio >= 1 ? "text-fin-green" : "text-fin-gold"}
        />
        <KpiCard
          label="Max Drawdown"
          value={fmtUSD(metrics.max_drawdown_usd)}
          sub={`${fmtPct(metrics.max_drawdown_pct)} · límite $2,500`}
          icon={AlertTriangle}
          color={metrics.max_drawdown_usd > 2000 ? "text-fin-red" : "text-fin-gold"}
        />
        <KpiCard
          label="Trades"
          value={String(metrics.total_trades)}
          sub={`${metrics.trades_per_day.toFixed(1)}/día`}
          icon={BarChart2}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card lg:col-span-2">
          <p className="text-sm font-medium mb-3">Curva de Equity</p>
          <EquityCurve data={equity_curve} initialBalance={metrics.initial_balance} />
        </div>

        <div className="card">
          <p className="text-sm font-medium mb-3">P&L por Trade</p>
          <PnlChart trades={trades} height={220} />
        </div>
      </div>

      {/* Drawdown gauge simple */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <p className="text-sm font-medium mb-3">Trailing Drawdown</p>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Actual</span>
              <span className={cn("font-mono", pnlColor(-metrics.max_drawdown_usd))}>
                ${metrics.max_drawdown_usd.toFixed(0)}
              </span>
            </div>
            <div className="h-3 bg-bg-tertiary rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(100, (metrics.max_drawdown_usd / 2500) * 100)}%`,
                  background:
                    metrics.max_drawdown_usd > 2000
                      ? "#EF5350"
                      : metrics.max_drawdown_usd > 1500
                      ? "#FFD54F"
                      : "#00C853",
                }}
              />
            </div>
            <div className="flex justify-between text-xs text-text-muted">
              <span>$0</span>
              <span>Límite $2,500</span>
            </div>
          </div>
        </div>

        <div className="card">
          <p className="text-sm font-medium mb-3">Stats Clave</p>
          <div className="space-y-2 text-sm">
            {[
              ["Expectancy", fmtUSD(metrics.expectancy)],
              ["Avg Win", fmtUSD(metrics.avg_win)],
              ["Avg Loss", fmtUSD(-metrics.avg_loss)],
              ["Avg R:R", metrics.avg_rr_ratio.toFixed(2) + ":1"],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-text-secondary">{k}</span>
                <span className="font-mono text-text-primary">{v}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <p className="text-sm font-medium mb-3">Mejor / Peor Día</p>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-text-secondary">Mejor día</p>
              <p className="text-xl font-bold font-mono text-fin-green">{fmtUSD(metrics.best_day_pnl)}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">Peor día</p>
              <p className="text-xl font-bold font-mono text-fin-red">{fmtUSD(metrics.worst_day_pnl)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent trades */}
      <div className="card">
        <p className="text-sm font-medium mb-3">Últimos 10 Trades</p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-text-muted border-b border-border">
                {["Fecha", "Dir", "Entry", "Exit", "SL", "TP", "P&L", "Razón"].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {recent.map((t, i) => (
                <tr key={i} className="border-b border-border/50 hover:bg-bg-tertiary/50">
                  <td className="py-2 pr-4 text-text-secondary">
                    {new Date(t.entry_time).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </td>
                  <td className="py-2 pr-4">
                    <span className={t.direction === "long" ? "badge-green" : "badge-red"}>
                      {t.direction.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-2 pr-4 font-mono">{t.entry_price.toFixed(0)}</td>
                  <td className="py-2 pr-4 font-mono">{t.exit_price.toFixed(0)}</td>
                  <td className="py-2 pr-4 font-mono text-text-secondary">{t.sl_price.toFixed(0)}</td>
                  <td className="py-2 pr-4 font-mono text-text-secondary">{t.tp_price.toFixed(0)}</td>
                  <td className={cn("py-2 pr-4 font-mono font-medium", pnlColor(t.pnl_net))}>
                    {fmtUSD(t.pnl_net)}
                  </td>
                  <td className="py-2 pr-4 text-text-secondary">{t.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
