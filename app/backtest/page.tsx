"use client";

import { useState } from "react";
import { useTradingStore } from "@/store";
import { EquityCurve } from "@/components/charts/equity-curve";
import { PnlChart } from "@/components/charts/pnl-chart";
import { BacktestChart } from "@/components/charts/backtest-chart";
import { fmtUSD, fmtPct, pnlColor, cn } from "@/lib/utils";
import { runBacktest } from "@/lib/api";
import { Play, Loader2, ChevronDown, ChevronUp } from "lucide-react";
;

function usePersistentState(key: string, fallback: string) {
  const stored = typeof window !== "undefined" ? (localStorage.getItem(key) ?? fallback) : fallback;
  const [value, setValue] = useState(stored);
  function set(v: string) {
    localStorage.setItem(key, v);
    setValue(v);
  }
  return [value, set] as const;
}

export default function BacktestPage() {
  const { backtestResult, setBacktestResult, activeConfig, setRunningBacktest, isRunningBacktest } = useTradingStore();

  const [startDate, setStartDate] = usePersistentState("backtest-start-date", "2025-10-01");
  const [endDate, setEndDate] = usePersistentState("backtest-end-date", "2025-11-30");
  const [error, setError] = useState("");
  const [errorTs, setErrorTs] = useState("");
  const [showErrorDetail, setShowErrorDetail] = useState(false);
  const [showTrades, setShowTrades] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "metrics" | "trades">("overview");

  async function handleRun() {
    setError("");
    setErrorTs("");
    setShowErrorDetail(false);
    setRunningBacktest(true);
    try {
      const result = await runBacktest(activeConfig, startDate, endDate);
      setBacktestResult(result);
    } catch (e) {
      setError(String(e));
      setErrorTs(new Date().toLocaleTimeString());
      setBacktestResult(null);
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
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
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
            <p className="text-xs text-fin-red font-medium">Error — ver diagnóstico abajo</p>
          )}
        </div>
      </div>

      {/* Error state — full diagnostic panel */}
      {error && !m && (
        <div className="card border border-fin-red/40 bg-fin-red/5 space-y-3 p-5">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-fin-red font-semibold text-sm">El backtest no pudo completarse</p>
              {errorTs && <p className="text-text-muted text-xs mt-0.5">Ocurrió a las {errorTs}</p>}
            </div>
            <button
              onClick={() => setShowErrorDetail((v) => !v)}
              className="text-xs text-text-secondary hover:text-text-primary flex items-center gap-1 shrink-0"
            >
              {showErrorDetail ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {showErrorDetail ? "Ocultar detalle" : "Ver detalle técnico"}
            </button>
          </div>

          {/* Categorized message */}
          {(() => {
            const e = error;
            if (e.includes("[RED]"))
              return (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-fin-red">Fallo de red — conexión cortada</p>
                  <p className="text-xs text-text-secondary">
                    {e.includes("cortada")
                      ? "La conexión se estableció pero fue cortada antes de recibir la respuesta completa. Posibles causas:"
                      : "El navegador no pudo alcanzar el servidor Next.js. Posibles causas:"}
                  </p>
                  <ul className="text-xs text-text-muted list-disc list-inside space-y-0.5">
                    {e.includes("cortada") ? (
                      <>
                        <li>Nginx cerró la conexión por timeout (revisa <code className="font-mono bg-bg-tertiary px-1 rounded">proxy_read_timeout</code> y <code className="font-mono bg-bg-tertiary px-1 rounded">send_timeout</code>)</li>
                        <li>El servidor Next.js se reinició durante el backtest</li>
                        <li>El backtest tardó más de lo esperado — intenta un rango de fechas menor</li>
                      </>
                    ) : (
                      <>
                        <li>El servidor Next.js (frontend) no está corriendo</li>
                        <li>Bloqueado por CORS o un proxy</li>
                        <li>La URL del servidor cambió</li>
                      </>
                    )}
                  </ul>
                </div>
              );
            if (e.includes("[HTTP 504]") || e.includes("504") || e.includes("tiempo máximo"))
              return (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-fin-red">Timeout — el backtest tardó demasiado</p>
                  <p className="text-xs text-text-secondary">
                    El servidor Python no respondió dentro del tiempo límite (10 min).
                  </p>
                  <ul className="text-xs text-text-muted list-disc list-inside space-y-0.5">
                    <li>Intenta con un rango de fechas más corto (máximo 2 meses)</li>
                    <li>Verifica que el servidor Python tiene acceso a internet (descarga datos de yfinance)</li>
                  </ul>
                </div>
              );
            if (e.includes("[HTTP 502]") || e.includes("502") || e.includes("uvicorn"))
              return (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-fin-red">502 — Next.js no pudo contactar al backend Python</p>
                  <p className="text-xs text-text-secondary">
                    El servidor Next.js está activo pero no puede hablar con el servidor Python (FastAPI/uvicorn).
                  </p>
                  <ul className="text-xs text-text-muted list-disc list-inside space-y-0.5">
                    <li>¿Está corriendo <code className="font-mono bg-bg-tertiary px-1 rounded">uvicorn server:app --port 8000</code>?</li>
                    <li>¿Está configurada la variable de entorno <code className="font-mono bg-bg-tertiary px-1 rounded">PYTHON_API_URL</code>?</li>
                    <li>¿Hay un firewall bloqueando el puerto 8000?</li>
                  </ul>
                </div>
              );
            if (e.includes("[HTTP"))
              return (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-fin-red">Error HTTP desde el backend</p>
                  <p className="text-xs text-text-secondary">El servidor respondió con un código de error.</p>
                </div>
              );
            if (e.includes("[BACKEND"))
              return (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-fin-red">Error en la ejecución del backtest</p>
                  <p className="text-xs text-text-secondary">El backend Python devolvió un error al procesar los datos.</p>
                </div>
              );
            return (
              <p className="text-xs text-text-secondary">Error desconocido — ver detalle técnico.</p>
            );
          })()}

          {/* Raw error — always visible, monospace */}
          <div className="bg-bg-tertiary rounded p-3 border border-border">
            <p className="text-xs text-text-muted font-mono break-all">{error}</p>
          </div>

          {/* Technical detail — expandable */}
          {showErrorDetail && (
            <div className="bg-bg-tertiary rounded p-3 border border-border space-y-2">
              <p className="text-xs font-semibold text-text-secondary">Información de diagnóstico</p>
              <div className="text-xs font-mono text-text-muted space-y-1">
                <p><span className="text-text-secondary">Ruta llamada:</span> {window.location.origin}/api/backtest</p>
                <p><span className="text-text-secondary">Fechas:</span> {startDate} → {endDate}</p>
                <p><span className="text-text-secondary">Config:</span> {activeConfig.name}</p>
                <p><span className="text-text-secondary">User-Agent:</span> {navigator.userAgent.slice(0, 80)}…</p>
              </div>
              <p className="text-[10px] text-text-muted mt-2">
                Copia este bloque y el mensaje de error de arriba para reportar el problema.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Results */}
      {m && res && (
        <>
          {/* ── Cuenta Quemada banner ─────────────────────────────────────── */}
          {(() => {
            // $2,500 = trailing drawdown limit (prop firm rule, fixed per account)
            const trailingDrawdownMax = 2500;
            const blown = m.total_pnl <= -trailingDrawdownMax;
            return blown ? (
              <div className="rounded-xl border border-fin-red bg-fin-red/10 px-5 py-4 flex items-start gap-4">
                <span className="text-3xl leading-none select-none">🔥</span>
                <div>
                  <p className="text-base font-bold text-fin-red tracking-wide">CUENTA QUEMADA</p>
                  <p className="text-sm text-text-secondary mt-0.5">
                    El P&L acumulado ({fmtUSD(m.total_pnl)}) alcanzó el límite de pérdida total
                    de {fmtUSD(-trailingDrawdownMax)}. El backtest se detuvo en ese punto y no se
                    abrieron más trades.
                  </p>
                </div>
              </div>
            ) : null;
          })()}

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
                {/* Header + glosario */}
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-4">
                  <div>
                    <p className="text-sm font-medium">FVG Detectados por Timeframe</p>
                    <p className="text-xs text-text-secondary mt-0.5">
                      Un <span className="text-text-primary font-medium">Fair Value Gap (FVG)</span> es una zona de precio donde el mercado se movió tan rápido que dejó un hueco sin negociar. El bot los busca para entrar en favor del desequilibrio.
                    </p>
                  </div>
                  {/* Leyenda */}
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-text-muted shrink-0">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-fin-green inline-block" />Alcistas (precio sube a llenar)</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-fin-red inline-block" />Bajistas (precio baja a llenar)</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-brand-blue inline-block" />Usados para entrar en un trade</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {res.fvg_summary?.map((f) => {
                    const usedPct = f.total > 0 ? Math.round((f.decision / f.total) * 100) : 0;
                    const bullPct = f.total > 0 ? Math.round((f.bullish / f.total) * 100) : 50;
                    return (
                      <div key={f.timeframe} className="bg-bg-tertiary rounded-md p-3 space-y-2.5">
                        {/* Timeframe + total */}
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-brand-blue font-mono font-bold uppercase tracking-wider">{f.timeframe}</span>
                          <span className="text-xl font-bold">{f.total}</span>
                        </div>
                        <p className="text-[10px] text-text-muted -mt-1">FVGs escaneados</p>

                        {/* Barra alcistas / bajistas */}
                        <div>
                          <div className="flex h-2 rounded-full overflow-hidden gap-px">
                            <div className="bg-fin-green rounded-l-full transition-all" style={{ width: `${bullPct}%` }} />
                            <div className="bg-fin-red rounded-r-full flex-1" />
                          </div>
                          <div className="flex justify-between text-[10px] mt-1">
                            <span className="text-fin-green font-mono">{f.bullish} alcistas</span>
                            <span className="text-fin-red font-mono">{f.bearish} bajistas</span>
                          </div>
                        </div>

                        {/* Separador */}
                        <div className="border-t border-border" />

                        {/* Usados en trades */}
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-text-secondary">Usados en trades</span>
                          <span className="text-xs font-mono">
                            <span className="text-brand-blue font-semibold">{f.decision}</span>
                            <span className="text-text-muted ml-1">({usedPct}%)</span>
                          </span>
                        </div>

                        {/* Confluencia */}
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-text-secondary">Confluencia media</span>
                          <span className="text-xs font-mono text-fin-gold">{f.avg_confluence.toFixed(1)}×</span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Nota de confluencia */}
                <p className="text-[10px] text-text-muted mt-3">
                  <span className="text-fin-gold font-medium">Confluencia</span> = cuántos FVGs de distintos timeframes coincidían en la misma zona de precio al momento de la entrada. Más confluencia → señal más fuerte.
                </p>
              </div>
            </div>
          )}

          {activeTab === "metrics" && (
            <div className="space-y-4">
            {/* Rejection Diagnostics — shown only when available */}
            {res.rejection_diagnostics && (
              <div className="card">
                <p className="text-sm font-semibold mb-1">Diagnóstico de Rechazos</p>
                <p className="text-xs text-text-muted mb-3">
                  Por cada barra del backtest dentro de las killzones, el bot evalúa si entrar.
                  Esta tabla muestra por qué NO entró en cada caso.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-text-muted border-b border-border">
                        <th className="text-left py-1.5 pr-4 font-medium">Razón</th>
                        <th className="text-right py-1.5 pr-4 font-medium w-20">Barras</th>
                        <th className="text-right py-1.5 font-medium w-16">%</th>
                        <th className="py-1.5 pl-4 w-32"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {res.rejection_diagnostics.rows.map((row) => (
                        <tr key={row.reason} className="border-b border-border/40">
                          <td className="py-1.5 pr-4 font-mono text-text-secondary">{row.reason}</td>
                          <td className="py-1.5 pr-4 font-mono text-right">{row.count.toLocaleString()}</td>
                          <td className="py-1.5 font-mono text-right text-text-muted">{row.pct.toFixed(1)}%</td>
                          <td className="py-1.5 pl-4">
                            <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full bg-brand-blue"
                                style={{ width: `${row.pct}%` }}
                              />
                            </div>
                          </td>
                        </tr>
                      ))}
                      <tr className="text-text-muted">
                        <td className="py-2 pr-4 font-medium">TOTAL</td>
                        <td className="py-2 pr-4 font-mono text-right">{res.rejection_diagnostics.total.toLocaleString()}</td>
                        <td colSpan={2} />
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}
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
            </div>
          )}

          {activeTab === "trades" && (
            <div className="card overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-text-muted border-b border-border">
                    {["#", "Fecha", "H. Entrada", "H. Salida", "Dir", "Entry", "Exit", "SL", "TP", "Contr.", "P&L", "Comisión", "Razón"].map((h) => (
                      <th key={h} className="text-left py-2 pr-3 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {res.trades.map((t, i) => (
                    <tr key={i} className="border-b border-border/40 hover:bg-bg-tertiary/50">
                      <td className="py-1.5 pr-3 text-text-muted">{i + 1}</td>
                      <td className="py-1.5 pr-3 text-text-secondary whitespace-nowrap">
                        {t.entry_time
                          ? new Date(t.entry_time).toLocaleDateString("es-VE", { day: "2-digit", month: "2-digit", year: "2-digit" })
                          : "—"}
                      </td>
                      <td className="py-1.5 pr-3 font-mono text-text-secondary whitespace-nowrap">
                        {t.entry_time
                          ? new Date(t.entry_time).toLocaleTimeString("es-VE", { hour: "2-digit", minute: "2-digit" })
                          : "—"}
                      </td>
                      <td className="py-1.5 pr-3 font-mono text-text-secondary whitespace-nowrap">
                        {t.exit_time
                          ? new Date(t.exit_time).toLocaleTimeString("es-VE", { hour: "2-digit", minute: "2-digit" })
                          : "—"}
                      </td>
                      <td className="py-1.5 pr-3">
                        <span className={t.direction === "long" ? "badge-green" : "badge-red"}>
                          {t.direction.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-1.5 pr-3 font-mono">{t.entry_price.toFixed(0)}</td>
                      <td className="py-1.5 pr-3 font-mono">{t.exit_price.toFixed(0)}</td>
                      <td className="py-1.5 pr-3 font-mono text-text-secondary">{t.sl_price ? t.sl_price.toFixed(0) : "—"}</td>
                      <td className="py-1.5 pr-3 font-mono text-text-secondary">{t.tp_price ? t.tp_price.toFixed(0) : "—"}</td>
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
