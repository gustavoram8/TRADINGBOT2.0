"use client";

import { useState } from "react";
import { useTradingStore } from "@/store";
import { fmtUSD, fmtPct, pnlColor, cn } from "@/lib/utils";
import { Download, FileText, Sheet, BarChart2 } from "lucide-react";

function downloadCSV(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
}

export default function ReportsPage() {
  const { backtestResult } = useTradingStore();
  const [activeTab, setActiveTab] = useState<"export" | "preview">("preview");

  if (!backtestResult) {
    return <div className="flex items-center justify-center h-64 text-text-secondary">Ejecuta un backtest primero.</div>;
  }

  const { metrics: m, trades, equity_curve, config } = backtestResult;

  function exportTrades() {
    const headers = ["#", "Direction", "Entry Time", "Exit Time", "Entry Price", "Exit Price", "SL", "TP", "Contracts", "P&L Gross", "P&L Net", "Commission", "Reason"];
    const rows = trades.map((t, i) => [
      i + 1, t.direction, t.entry_time, t.exit_time,
      t.entry_price, t.exit_price, t.sl_price, t.tp_price,
      t.contracts, t.pnl_gross.toFixed(2), t.pnl_net.toFixed(2), t.commission.toFixed(2), t.reason,
    ]);
    const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
    downloadCSV(csv, "trades.csv");
  }

  function exportEquity() {
    const headers = ["Datetime", "Equity", "PnL", "Drawdown", "Drawdown %"];
    const rows = equity_curve.map((p) => [p.datetime, p.equity.toFixed(2), p.pnl.toFixed(2), p.drawdown.toFixed(2), (p.drawdown_pct * 100).toFixed(2)]);
    downloadCSV([headers, ...rows].map((r) => r.join(",")).join("\n"), "equity.csv");
  }

  function exportMetrics() {
    const rows = Object.entries(m).map(([k, v]) => [k, String(v)]);
    downloadCSV(["Metric,Value", ...rows.map((r) => r.join(","))].join("\n"), "metrics.csv");
  }

  function exportConfig() {
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `config_${config.name}.json`;
    a.click();
  }

  const tabs = [["preview", "Vista Previa"], ["export", "Exportar"]] as const;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Reports</h1>
        <p className="text-sm text-text-secondary mt-0.5">Exporta resultados y genera reportes</p>
      </div>

      <div className="border-b border-border flex gap-1">
        {tabs.map(([t, l]) => (
          <button key={t} onClick={() => setActiveTab(t)} className={cn("px-4 py-2 text-sm", activeTab === t ? "tab-active" : "tab-inactive")}>
            {l}
          </button>
        ))}
      </div>

      {activeTab === "export" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { label: "Trades CSV", desc: `${trades.length} operaciones con entrada/salida/P&L`, icon: Sheet, action: exportTrades, filename: "trades.csv" },
            { label: "Equity Curve CSV", desc: `${equity_curve.length} puntos de curva de capital`, icon: BarChart2, action: exportEquity, filename: "equity.csv" },
            { label: "Métricas CSV", desc: "Todos los KPIs del backtest en una fila", icon: FileText, action: exportMetrics, filename: "metrics.csv" },
            { label: "Config JSON", desc: `Parámetros de "${config.name}"`, icon: FileText, action: exportConfig, filename: `config_${config.name}.json` },
          ].map(({ label, desc, icon: Icon, action }) => (
            <div key={label} className="card flex items-center gap-4">
              <div className="w-10 h-10 rounded-md bg-brand-dark/20 flex items-center justify-center flex-shrink-0">
                <Icon size={20} className="text-brand-blue" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-sm">{label}</p>
                <p className="text-xs text-text-secondary">{desc}</p>
              </div>
              <button onClick={action} className="btn-secondary flex items-center gap-1.5">
                <Download size={13} /> Descargar
              </button>
            </div>
          ))}
        </div>
      )}

      {activeTab === "preview" && (
        <div className="space-y-4">
          {/* Executive summary */}
          <div className={cn("card border-2", m.total_pnl > 0 ? "border-fin-green/30" : "border-fin-red/30")}>
            <div className="flex items-center justify-between mb-4">
              <p className="font-bold text-lg">Resumen Ejecutivo</p>
              <span className={m.total_pnl > 0 ? "badge-green text-sm px-3 py-1" : "badge-red text-sm px-3 py-1"}>
                {m.total_pnl > 0 ? "RENTABLE" : "EN PÉRDIDA"}
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                ["P&L Total", fmtUSD(m.total_pnl), pnlColor(m.total_pnl)],
                ["Win Rate", fmtPct(m.win_rate), "text-fin-blue"],
                ["Profit Factor", m.profit_factor.toFixed(2), m.profit_factor >= 1.5 ? "text-fin-green" : "text-fin-gold"],
                ["Sharpe Ratio", m.sharpe_ratio.toFixed(2), m.sharpe_ratio >= 1 ? "text-fin-green" : "text-fin-gold"],
              ].map(([k, v, c]) => (
                <div key={k}>
                  <p className="text-xs text-text-secondary">{k}</p>
                  <p className={cn("text-xl font-bold font-mono mt-0.5", c)}>{v}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Metrics grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card">
              <p className="text-sm font-semibold mb-3">Análisis P&L</p>
              <div className="space-y-2 text-sm">
                {[
                  ["P&L Bruto", fmtUSD(m.total_pnl_gross)],
                  ["Comisiones Totales", fmtUSD(-m.total_commission)],
                  ["P&L Neto", fmtUSD(m.total_pnl)],
                  ["Retorno Total", fmtPct(m.total_return_pct)],
                  ["Expectancy", fmtUSD(m.expectancy)],
                  ["Avg Win", fmtUSD(m.avg_win)],
                  ["Avg Loss", fmtUSD(-m.avg_loss)],
                  ["Mejor trade", fmtUSD(m.largest_win)],
                  ["Peor trade", fmtUSD(m.largest_loss)],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b border-border/30 pb-1">
                    <span className="text-text-secondary">{k}</span>
                    <span className="font-mono">{v}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <p className="text-sm font-semibold mb-3">Análisis de Riesgo</p>
              <div className="space-y-2 text-sm">
                {[
                  ["Max Drawdown $", fmtUSD(m.max_drawdown_usd)],
                  ["Max Drawdown %", fmtPct(m.max_drawdown_pct)],
                  ["Avg Drawdown", fmtUSD(m.avg_drawdown_usd)],
                  ["Mejor día", fmtUSD(m.best_day_pnl)],
                  ["Peor día", fmtUSD(m.worst_day_pnl)],
                  ["Sortino Ratio", m.sortino_ratio.toFixed(2)],
                  ["Avg R:R", m.avg_rr_ratio.toFixed(2) + ":1"],
                  ["Trades/Día", m.trades_per_day.toFixed(1)],
                  ["Consistencia OneUP", m.consistency_check_passed ? "✓ PASS" : "✗ FAIL"],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b border-border/30 pb-1">
                    <span className="text-text-secondary">{k}</span>
                    <span className="font-mono">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent trades table */}
          <div className="card overflow-x-auto">
            <p className="text-sm font-semibold mb-3">Todas las Operaciones</p>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-text-muted">
                  {["#", "Dirección", "Entry", "Exit", "SL", "TP", "Contr.", "P&L", "Razón"].map((h) => (
                    <th key={h} className="text-left py-2 pr-3 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {trades.map((t, i) => (
                  <tr key={i} className="border-b border-border/30 hover:bg-bg-tertiary/40">
                    <td className="py-1.5 pr-3 text-text-muted">{i + 1}</td>
                    <td className="py-1.5 pr-3">
                      <span className={t.direction === "long" ? "badge-green" : "badge-red"}>{t.direction.toUpperCase()}</span>
                    </td>
                    <td className="py-1.5 pr-3 font-mono">{t.entry_price.toFixed(0)}</td>
                    <td className="py-1.5 pr-3 font-mono">{t.exit_price.toFixed(0)}</td>
                    <td className="py-1.5 pr-3 font-mono text-text-muted">{t.sl_price.toFixed(0)}</td>
                    <td className="py-1.5 pr-3 font-mono text-text-muted">{t.tp_price.toFixed(0)}</td>
                    <td className="py-1.5 pr-3 text-center">{t.contracts}</td>
                    <td className={cn("py-1.5 pr-3 font-mono font-medium", pnlColor(t.pnl_net))}>{fmtUSD(t.pnl_net)}</td>
                    <td className="py-1.5 pr-3 text-text-muted">{t.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
