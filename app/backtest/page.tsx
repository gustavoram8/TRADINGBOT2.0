"use client";

import { useState } from "react";
import { useTradingStore } from "@/store";
import { EquityCurve } from "@/components/charts/equity-curve";
import { PnlChart } from "@/components/charts/pnl-chart";
import { BacktestChart } from "@/components/charts/backtest-chart";
import { fmtUSD, fmtPct, pnlColor, cn } from "@/lib/utils";
import { runBacktest } from "@/lib/api";
import { Play, Loader2, ChevronDown, ChevronUp } from "lucide-react";
import { MOCK_BACKTEST_RESULT } from "@/lib/mock-data";

export default function BacktestPage() {
  const { backtestResult, setBacktestResult, activeConfig, setRunningBacktest, isRunningBacktest } = useTradingStore();

  const [startDate, setStartDate] = useState("2025-10-01");
  const [endDate, setEndDate] = useState("2025-11-30");
  const [interval, setInterval] = useState("1h");
  const [error, setError] = useState("");
  const [showTrades, setShowTrades] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "metrics" | "trades">("overview");

  async function handleRun() {
    setError("");
    setRunningBacktest(true);
    try {
      const result = await runBacktest(activeConfig, startDate, endDate, interval);
      setBacktestResult(result);
    } catch (e) {
      setError(String(e));
      setBacktestResult(MOCK_BACKTEST_RESULT);
    } finally {
      setRunningBacktest(false);
    }
  }

  const res = backtestResult;
  const m = res?.metrics;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Backtest Lab</h1>
        <p className="text-sm text-text-secondary mt-0.5">Simula la estrategia ICT sobre datos históricos</p>
      </div>

      {/* Config panel */}
      <div className="card">
        <p className="text-sm font-semibold mb-4">Configuración del Backtest</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-text-secondary block mb-1">Fecha inicio</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full bg-bg-tertiary border border-border rounded-md px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-brand-blue"
            />
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">Fecha fin</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full bg-bg-tertiary border border-border rounded-md px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-brand-blue"
            />
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">Timeframe base</label>
            <select
              value={interval}
              onChange={(e) => setInterval(e.target.value)}
              className="w-full bg-bg-tertiary border border-border rounded-md px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-brand-blue"
            >
              {["1m", "5m", "15m", "1h"].map((tf) => (
                <option key={tf} value={tf}>{tf}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">Config activa</label>
            <div className="bg-bg-tertiary border border-border rounded-md px-3 py-1.5 text-sm text-brand-blue">
              {activeConfig.name}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 mt-4">
          <button onClick={handleRun} disabled={isRunningBacktest} className="btn-primary flex items-center gap-2">
            {isRunningBacktest ? (
              <><Loader2 size={14} className="animate-spin" /> Ejecutando...</>
            ) : (
              <><Play size={14} /> Ejecutar Backtest</>
            )}
          </button>
          {error && (
            <p className="text-xs text-fin-gold">
              {process.env.PYTHON_API_URL
                ? error
                : "Backend Python no conectado — mostrando datos de demostración"}
            </p>
          )}
        </div>
      </div>

      {/* Results */}
      {m && res && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {[
              { l: "P&L Neto", v: fmtUSD(m.total_pnl), c: pnlColor(m.total_pnl) },
              { l: "Win Rate", v: fmtPct(m.win_rate), c: "text-fin-blue" },
              { l: "Profit Factor", v: m.profit_factor.toFixed(2), c: m.profit_factor >= 1.5 ? "text-fin-green" : "text-fin-gold" },
              { l: "Sharpe", v: m.sharpe_ratio.toFixed(2), c: m.sharpe_ratio >= 1 ? "text-fin-green" : "text-fin-gold" },
              { l: "Max DD", v: fmtUSD(m.max_drawdown_usd), c: m.max_drawdown_usd > 2000 ? "text-fin-red" : "text-fin-gold" },
              { l: "Trades", v: String(m.total_trades), c: "text-text-primary" },
            ].map(({ l, v, c }) => (
              <div key={l} className="kpi-card">
                <p className="text-xs text-text-secondary">{l}</p>
                <p className={cn("text-xl font-bold font-mono mt-1", c)}>{v}</p>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div className="border-b border-border flex gap-1">
            {(["overview", "metrics", "trades"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                className={cn(
                  "px-4 py-2 text-sm capitalize transition-colors",
                  activeTab === t ? "tab-active" : "tab-inactive"
                )}
              >
                {t === "overview" ? "Gráficos" : t === "metrics" ? "Métricas" : "Lista de Trades"}
              </button>
            ))}
          </div>

          {activeTab === "overview" && (
            <div className="space-y-4">
              {/* Primary: Candlestick chart with all ICT overlays */}
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium">Gráfico de Velas — ICT Overlays</p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-secondary">
                    <span className="flex items-center gap-1.5">
                      <span className="inline-block w-4 h-0.5 bg-[#26a69a]" />FVG Bull
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="inline-block w-4 h-0.5 bg-[#ef5350]" />FVG Bear
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="inline-block w-4 h-0.5 bg-[#2979FF]" />PDH/PDL
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="inline-block w-4 h-0.5 bg-[#FF9800]" />EQ / Sweep
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="inline-block w-4 h-0.5 bg-[#AB47BC]" />ATH/ATL
                    </span>
                  </div>
                </div>
                <BacktestChart
                  ohlcData={res.ohlc_data ?? []}
                  ohlcByTimeframe={res.ohlc_by_timeframe}
                  trades={res.trades}
                  fvgZones={res.fvg_zones ?? []}
                  liquidityLevels={res.liquidity_levels ?? []}
                  sweeps={res.sweeps ?? []}
                  height={480}
                />
              </div>

              {/* Secondary: Equity curve + P&L */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="card">
                  <p className="text-sm font-medium mb-3">Equity Curve</p>
                  <EquityCurve data={res.equity_curve} initialBalance={m.initial_balance} height={200} />
                </div>
                <div className="card">
                  <p className="text-sm font-medium mb-3">P&L por Trade</p>
                  <PnlChart trades={res.trades} height={200} />
                </div>
              </div>

              {/* FVG summary cards */}
              <div className="card">
                <p className="text-sm font-medium mb-3">FVG Detectados por Timeframe</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {res.fvg_summary?.map((f) => (
                    <div key={f.timeframe} className="bg-bg-tertiary rounded-md p-3">
                      <p className="text-xs text-brand-blue font-mono font-semibold uppercase">{f.timeframe}</p>
                      <p className="text-lg font-bold mt-1">{f.total}</p>
                      <div className="flex gap-2 mt-1 text-xs">
                        <span className="text-fin-green">{f.bullish}↑</span>
                        <span className="text-fin-red">{f.bearish}↓</span>
                        <span className="text-brand-blue">{f.decision} dec</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "metrics" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                {
                  title: "Rendimiento",
                  rows: [
                    ["P&L Bruto", fmtUSD(m.total_pnl_gross)],
                    ["Comisiones", fmtUSD(-m.total_commission)],
                    ["P&L Neto", fmtUSD(m.total_pnl)],
                    ["Retorno %", fmtPct(m.total_return_pct)],
                    ["Expectancy", fmtUSD(m.expectancy)],
                    ["Avg Win", fmtUSD(m.avg_win)],
                    ["Avg Loss", fmtUSD(-m.avg_loss)],
                    ["Larger Win", fmtUSD(m.largest_win)],
                    ["Largest Loss", fmtUSD(m.largest_loss)],
                  ],
                },
                {
                  title: "Riesgo",
                  rows: [
                    ["Max Drawdown $", fmtUSD(m.max_drawdown_usd)],
                    ["Max Drawdown %", fmtPct(m.max_drawdown_pct)],
                    ["Avg Drawdown $", fmtUSD(m.avg_drawdown_usd)],
                    ["Sharpe Ratio", m.sharpe_ratio.toFixed(2)],
                    ["Sortino Ratio", m.sortino_ratio.toFixed(2)],
                    ["Profit Factor", m.profit_factor.toFixed(2)],
                    ["Win Rate", fmtPct(m.win_rate)],
                    ["Avg R:R", m.avg_rr_ratio.toFixed(2) + ":1"],
                    ["Trades/Día", m.trades_per_day.toFixed(1)],
                  ],
                },
              ].map(({ title, rows }) => (
                <div key={title} className="card">
                  <p className="text-sm font-semibold mb-3">{title}</p>
                  <div className="space-y-2">
                    {rows.map(([k, v]) => (
                      <div key={k} className="flex justify-between text-sm">
                        <span className="text-text-secondary">{k}</span>
                        <span className="font-mono">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === "trades" && (
            <div className="card overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-text-muted border-b border-border">
                    {["#", "Dir", "Entry", "Exit", "SL", "TP", "Contr.", "P&L", "Comisión", "Razón"].map((h) => (
                      <th key={h} className="text-left py-2 pr-3 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {res.trades.map((t, i) => (
                    <tr key={i} className="border-b border-border/40 hover:bg-bg-tertiary/50">
                      <td className="py-1.5 pr-3 text-text-muted">{i + 1}</td>
                      <td className="py-1.5 pr-3">
                        <span className={t.direction === "long" ? "badge-green" : "badge-red"}>
                          {t.direction.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-1.5 pr-3 font-mono">{t.entry_price.toFixed(0)}</td>
                      <td className="py-1.5 pr-3 font-mono">{t.exit_price.toFixed(0)}</td>
                      <td className="py-1.5 pr-3 font-mono text-text-secondary">{t.sl_price.toFixed(0)}</td>
                      <td className="py-1.5 pr-3 font-mono text-text-secondary">{t.tp_price.toFixed(0)}</td>
                      <td className="py-1.5 pr-3 text-center">{t.contracts}</td>
                      <td className={cn("py-1.5 pr-3 font-mono font-medium", pnlColor(t.pnl_net))}>
                        {fmtUSD(t.pnl_net)}
                      </td>
                      <td className="py-1.5 pr-3 font-mono text-text-muted">${t.commission.toFixed(2)}</td>
                      <td className="py-1.5 pr-3 text-text-secondary">{t.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
