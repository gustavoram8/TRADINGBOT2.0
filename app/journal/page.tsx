"use client";

import React, { useState, useMemo } from "react";
import { useTradingStore } from "@/store";
import { cn } from "@/lib/utils";
import type { Trade, TradeContext, TradeSetupCondition } from "@/lib/types";
import {
  ChevronDown,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  XCircle,
  Clock,
  Target,
  Layers,
  Zap,
  BookOpen,
} from "lucide-react";

// ── Helpers ──────────────────────────────────────────────────────────────

function fmt(n: number, digits = 0): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtPnl(n: number): string {
  return `${n >= 0 ? "+" : ""}$${fmt(Math.abs(n), 2)}`;
}

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}

function groupByDay(trades: Trade[]): Map<string, Trade[]> {
  const map = new Map<string, Trade[]>();
  for (const t of trades) {
    const day = t.entry_time.slice(0, 10);
    if (!map.has(day)) map.set(day, []);
    map.get(day)!.push(t);
  }
  return map;
}

// ── Score bar ────────────────────────────────────────────────────────────

function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = Math.min(100, (score / max) * 100);
  const color =
    pct >= 80 ? "bg-fin-green" : pct >= 55 ? "bg-fin-gold" : "bg-fin-red";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={cn(
          "text-xs font-mono font-bold tabular-nums",
          pct >= 80
            ? "text-fin-green"
            : pct >= 55
            ? "text-fin-gold"
            : "text-fin-red"
        )}
      >
        {score}/{max}
      </span>
    </div>
  );
}

// ── Condition row ────────────────────────────────────────────────────────

function ConditionRow({ cond }: { cond: TradeSetupCondition }) {
  return (
    <div className="flex items-start gap-2.5 py-1.5 border-b border-border/40 last:border-0">
      <div className="mt-0.5 flex-shrink-0">
        {cond.passed ? (
          <CheckCircle2 size={14} className="text-fin-green" />
        ) : (
          <XCircle size={14} className="text-fin-red" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <span
          className={cn(
            "text-xs font-medium",
            cond.passed ? "text-text-primary" : "text-text-secondary"
          )}
        >
          {cond.label}
        </span>
        <p className="text-[11px] text-text-muted mt-0.5 leading-snug">
          {cond.detail}
        </p>
      </div>
      <span
        className={cn(
          "text-[10px] font-mono font-bold flex-shrink-0 mt-0.5",
          cond.passed ? "text-fin-green" : "text-text-muted"
        )}
      >
        +{cond.score}
      </span>
    </div>
  );
}

// ── Context panel ────────────────────────────────────────────────────────

function ContextPanel({ ctx }: { ctx: TradeContext }) {
  const maxScore = ctx.conditions.reduce((s, c) => s + c.score, 0);

  return (
    <div className="mt-3 pt-3 border-t border-border space-y-4">
      {/* Row 1: quick facts */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Chip
          icon={<TrendingUp size={12} />}
          label="Estructura"
          value={
            ctx.market_structure === "bullish"
              ? "Alcista"
              : ctx.market_structure === "bearish"
              ? "Bajista"
              : "Rango"
          }
          color={
            ctx.market_structure === "bullish"
              ? "text-fin-green"
              : ctx.market_structure === "bearish"
              ? "text-fin-red"
              : "text-fin-gold"
          }
        />
        <Chip
          icon={<Layers size={12} />}
          label="Zona de precio"
          value={
            ctx.price_zone === "discount"
              ? "Descuento"
              : ctx.price_zone === "premium"
              ? "Prima"
              : "Equilibrio"
          }
          color={
            ctx.price_zone === "equilibrium" ? "text-fin-gold" : "text-brand-blue"
          }
        />
        <Chip
          icon={<Clock size={12} />}
          label="Killzone"
          value={ctx.killzone}
          color="text-text-secondary"
        />
        <Chip
          icon={<Target size={12} />}
          label="Objetivo liq."
          value={ctx.nearest_target}
          color="text-fin-gold"
        />
      </div>

      {/* Row 2: FVG trigger + confluence + sweep */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <div className="bg-bg-tertiary rounded-md px-3 py-2">
          <p className="text-[10px] text-text-muted uppercase tracking-wide mb-1">
            FVG disparador
          </p>
          <p className="text-xs font-medium text-text-primary">
            <span
              className={
                ctx.trigger_fvg_type === "bullish"
                  ? "text-fin-green"
                  : "text-fin-red"
              }
            >
              {ctx.trigger_fvg_type === "bullish" ? "Alcista" : "Bajista"}
            </span>{" "}
            · {ctx.trigger_fvg_timeframe.toUpperCase()} · {ctx.trigger_fvg_size_points} pts
          </p>
        </div>
        <div className="bg-bg-tertiary rounded-md px-3 py-2">
          <p className="text-[10px] text-text-muted uppercase tracking-wide mb-1">
            FVGs confluencia
          </p>
          {ctx.fvg_confluence.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {ctx.fvg_confluence.map((f, i) => (
                <span
                  key={i}
                  className={cn(
                    "text-[10px] font-mono px-1.5 py-0.5 rounded",
                    f.type === "bullish"
                      ? "bg-fin-green/15 text-fin-green"
                      : "bg-fin-red/15 text-fin-red"
                  )}
                >
                  {f.timeframe.toUpperCase()}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-text-muted">Ninguno</p>
          )}
        </div>
        <div className="bg-bg-tertiary rounded-md px-3 py-2">
          <p className="text-[10px] text-text-muted uppercase tracking-wide mb-1">
            Sweep reciente
          </p>
          {ctx.recent_sweep ? (
            <p className="text-xs font-medium text-fin-gold flex items-center gap-1">
              <Zap size={11} />
              {ctx.recent_sweep}
            </p>
          ) : (
            <p className="text-xs text-text-muted">Sin sweep</p>
          )}
        </div>
      </div>

      {/* Conditions checklist */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10px] uppercase tracking-wide text-text-muted font-medium">
            Condiciones de entrada
          </p>
          <ScoreBar score={ctx.setup_score} max={maxScore} />
        </div>
        <div className="bg-bg-tertiary rounded-md px-3 py-1">
          {ctx.conditions.map((cond, i) => (
            <ConditionRow key={i} cond={cond} />
          ))}
        </div>
      </div>

      {/* Exit detail */}
      <div className="bg-bg-tertiary rounded-md px-3 py-2">
        <p className="text-[10px] text-text-muted uppercase tracking-wide mb-1">
          Detalle de salida
        </p>
        <p className="text-xs text-text-primary leading-relaxed">
          {ctx.exit_detail}
        </p>
      </div>
    </div>
  );
}

function Chip({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-bg-tertiary rounded-md px-3 py-2">
      <p className="text-[10px] text-text-muted uppercase tracking-wide mb-1">
        {label}
      </p>
      <p className={cn("text-xs font-medium flex items-center gap-1", color)}>
        {icon}
        {value}
      </p>
    </div>
  );
}

// ── Trade card ───────────────────────────────────────────────────────────

function TradeCard({ trade, index }: { trade: Trade; index: number }) {
  const [open, setOpen] = useState(false);
  const isWin = trade.pnl_net > 0;
  const maxScore = trade.context
    ? trade.context.conditions.reduce((s, c) => s + c.score, 0)
    : 10;
  const score = trade.context?.setup_score ?? 0;
  const scorePct = (score / maxScore) * 100;

  return (
    <div
      className={cn(
        "rounded-lg border transition-colors",
        isWin ? "border-fin-green/30" : "border-fin-red/30",
        open && "border-opacity-60"
      )}
    >
      {/* Header row — always visible */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-bg-tertiary/50 transition-colors rounded-lg"
      >
        {/* Index */}
        <span className="text-[11px] text-text-muted font-mono w-5 flex-shrink-0">
          #{index + 1}
        </span>

        {/* Direction badge */}
        <span
          className={cn(
            "text-[10px] font-bold uppercase px-2 py-0.5 rounded flex items-center gap-0.5 flex-shrink-0",
            trade.direction === "long"
              ? "bg-fin-green/15 text-fin-green"
              : "bg-fin-red/15 text-fin-red"
          )}
        >
          {trade.direction === "long" ? (
            <TrendingUp size={10} />
          ) : (
            <TrendingDown size={10} />
          )}
          {trade.direction === "long" ? "LONG" : "SHORT"}
        </span>

        {/* Timing */}
        <span className="text-xs text-text-muted font-mono flex-shrink-0">
          {fmtTime(trade.entry_time)} → {fmtTime(trade.exit_time)}
        </span>

        {/* Entry → exit prices */}
        <span className="text-xs text-text-secondary hidden sm:inline font-mono flex-shrink-0">
          {trade.entry_price.toFixed(2)} → {trade.exit_price.toFixed(2)}
        </span>

        {/* Contracts */}
        <span className="text-[11px] text-text-muted flex-shrink-0">
          {trade.contracts}x
        </span>

        {/* Reason */}
        <span className="text-[11px] text-text-muted flex-1 truncate">
          {trade.reason}
        </span>

        {/* Setup score pill */}
        {trade.context && (
          <span
            className={cn(
              "text-[10px] font-mono font-bold px-2 py-0.5 rounded flex-shrink-0",
              scorePct >= 80
                ? "bg-fin-green/15 text-fin-green"
                : scorePct >= 55
                ? "bg-fin-gold/15 text-fin-gold"
                : "bg-fin-red/15 text-fin-red"
            )}
          >
            {score}/{maxScore}
          </span>
        )}

        {/* PnL */}
        <span
          className={cn(
            "text-sm font-bold font-mono tabular-nums flex-shrink-0",
            isWin ? "text-fin-green" : "text-fin-red"
          )}
        >
          {fmtPnl(trade.pnl_net)}
        </span>

        {/* Expand chevron */}
        <span className="text-text-muted flex-shrink-0 ml-1">
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>
      </button>

      {/* Expanded context */}
      {open && (
        <div className="px-4 pb-4">
          {trade.context ? (
            <ContextPanel ctx={trade.context} />
          ) : (
            <p className="text-xs text-text-muted italic mt-2">
              Sin contexto disponible para este trade.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Day section ──────────────────────────────────────────────────────────

function DaySection({ day, trades }: { day: string; trades: Trade[] }) {
  const dayPnl = trades.reduce((s, t) => s + t.pnl_net, 0);
  const wins = trades.filter((t) => t.pnl_net > 0).length;

  return (
    <section className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-text-primary capitalize">
            {fmtDate(day + "T12:00:00Z")}
          </h3>
          <span className="text-xs text-text-muted">
            {trades.length} trade{trades.length !== 1 ? "s" : ""} · {wins}W / {trades.length - wins}L
          </span>
        </div>
        <span
          className={cn(
            "text-sm font-bold font-mono",
            dayPnl >= 0 ? "text-fin-green" : "text-fin-red"
          )}
        >
          {fmtPnl(dayPnl)}
        </span>
      </div>
      <div className="space-y-2">
        {trades.map((t, i) => (
          <TradeCard key={t.id ?? i} trade={t} index={i} />
        ))}
      </div>
    </section>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────

export default function JournalPage() {
  const { backtestResult } = useTradingStore();
  const trades = backtestResult?.trades ?? [];

  const [filter, setFilter] = useState<"all" | "win" | "loss">("all");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    return trades.filter((t) => {
      if (filter === "win" && t.pnl_net <= 0) return false;
      if (filter === "loss" && t.pnl_net > 0) return false;
      if (search) {
        const q = search.toLowerCase();
        if (
          !t.reason.toLowerCase().includes(q) &&
          !t.direction.includes(q) &&
          !(t.context?.killzone ?? "").toLowerCase().includes(q) &&
          !(t.context?.market_structure ?? "").toLowerCase().includes(q)
        )
          return false;
      }
      return true;
    });
  }, [trades, filter, search]);

  const grouped = useMemo(() => groupByDay(filtered), [filtered]);
  const days = Array.from(grouped.keys()).sort();

  const totalPnl = filtered.reduce((s, t) => s + t.pnl_net, 0);
  const wins = filtered.filter((t) => t.pnl_net > 0).length;

  if (!backtestResult) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-muted">
        <div className="text-center space-y-2">
          <BookOpen size={40} className="mx-auto opacity-30" />
          <p className="text-sm">Ejecuta un backtest para ver el diario de trades.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* Page header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-text-primary flex items-center gap-2">
              <BookOpen size={20} className="text-brand-blue" />
              Diario de Trades
            </h1>
            <p className="text-sm text-text-muted mt-0.5">
              {backtestResult.period_name ?? "Período de backtest"} ·{" "}
              {trades.length} operaciones
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-text-muted">PnL total (filtrado)</p>
            <p
              className={cn(
                "text-lg font-bold font-mono tabular-nums",
                totalPnl >= 0 ? "text-fin-green" : "text-fin-red"
              )}
            >
              {fmtPnl(totalPnl)}
            </p>
          </div>
        </div>

        {/* Summary chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Trades", value: filtered.length.toString() },
            {
              label: "Win rate",
              value:
                filtered.length > 0
                  ? `${((wins / filtered.length) * 100).toFixed(1)}%`
                  : "—",
            },
            { label: "Ganadores", value: wins.toString() },
            {
              label: "Perdedores",
              value: (filtered.length - wins).toString(),
            },
          ].map(({ label, value }) => (
            <div key={label} className="card p-3 text-center">
              <p className="text-[11px] text-text-muted uppercase tracking-wide">
                {label}
              </p>
              <p className="text-lg font-bold text-text-primary mt-0.5">
                {value}
              </p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex gap-1 p-1 bg-bg-tertiary rounded-lg">
            {(["all", "win", "loss"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  "px-3 py-1 rounded-md text-xs font-medium transition-colors",
                  filter === f
                    ? "bg-brand-dark text-white"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                {f === "all" ? "Todos" : f === "win" ? "Ganadores" : "Perdedores"}
              </button>
            ))}
          </div>
          <input
            type="text"
            placeholder="Buscar por razón, dirección, killzone…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 min-w-[200px] bg-bg-tertiary border border-border rounded-lg px-3 py-1.5 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-brand-blue"
          />
        </div>

        {/* Trade list grouped by day */}
        {days.length === 0 ? (
          <div className="text-center py-16 text-text-muted text-sm">
            No hay trades que coincidan con el filtro.
          </div>
        ) : (
          days.map((day) => (
            <DaySection key={day} day={day} trades={grouped.get(day)!} />
          ))
        )}
      </div>
    </div>
  );
}
