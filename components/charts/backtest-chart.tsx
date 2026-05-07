"use client";

import { useEffect, useRef, useState } from "react";
import type { UTCTimestamp } from "lightweight-charts";
import type { OHLCBar, Trade, FVGZone, LiquidityLevel, SweepEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

function toTs(ms: number): UTCTimestamp {
  return Math.floor(ms / 1000) as UTCTimestamp;
}

interface Props {
  ohlcData: OHLCBar[];
  ohlcByTimeframe?: Record<string, OHLCBar[]>;
  trades?: Trade[];
  fvgZones?: FVGZone[];
  liquidityLevels?: LiquidityLevel[];
  sweeps?: SweepEvent[];
  height?: number;
}

const TF_ORDER = ["1m", "5m", "15m", "1h", "4h"] as const;

const TF_LABEL: Record<string, string> = {
  "4h": "4H", "1h": "1H", "15m": "15M", "5m": "5M", "1m": "1M",
};

const TF_ALPHA: Record<string, number> = {
  "4h": 0.85, "1h": 0.70, "15m": 0.50, "5m": 0.35, "1m": 0.20,
};

const LIQ_COLOR: Record<string, string> = {
  PDH: "#2979FF", PDL: "#2979FF",
  EQH: "#FF9800", EQL: "#FF9800",
  ATH: "#AB47BC", ATL: "#AB47BC",
  swing_high: "#546E7A", swing_low: "#546E7A",
};

export function BacktestChart({
  ohlcData,
  ohlcByTimeframe,
  trades = [],
  fvgZones = [],
  liquidityLevels = [],
  sweeps = [],
  height = 480,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  const availableTfs = TF_ORDER.filter((tf) => ohlcByTimeframe?.[tf]?.length);
  const initialTf =
    availableTfs.includes("1h") ? "1h" : availableTfs[0] ?? "";
  const [selectedTf, setSelectedTf] = useState<string>(initialTf);

  const activeOhlc =
    ohlcByTimeframe && selectedTf && ohlcByTimeframe[selectedTf]?.length
      ? ohlcByTimeframe[selectedTf]
      : ohlcData;

  useEffect(() => {
    if (!containerRef.current || activeOhlc.length === 0) return;

    let destroyed = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let chartInst: any = null;
    let resizeObs: ResizeObserver | null = null;

    import("lightweight-charts").then((lc) => {
      if (destroyed || !containerRef.current) return;

      const { createChart, ColorType, CrosshairMode, LineStyle } = lc;

      const chart = createChart(containerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: "#0D1117" },
          textColor: "#8B949E",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "#161B22" },
          horzLines: { color: "#161B22" },
        },
        crosshair: {
          mode: CrosshairMode.Normal,
          vertLine: { color: "#30363D", labelBackgroundColor: "#21262D" },
          horzLine: { color: "#30363D", labelBackgroundColor: "#21262D" },
        },
        rightPriceScale: { borderColor: "#30363D" },
        timeScale: {
          borderColor: "#30363D",
          timeVisible: true,
          secondsVisible: false,
        },
        width: containerRef.current.clientWidth,
        height,
      });
      chartInst = chart;

      // ── Candlestick series ───────────────────────────────────
      const candles = chart.addCandlestickSeries({
        upColor: "#26a69a",
        downColor: "#ef5350",
        borderUpColor: "#26a69a",
        borderDownColor: "#ef5350",
        wickUpColor: "#26a69a",
        wickDownColor: "#ef5350",
      });
      candles.setData(
        activeOhlc.map((b) => ({
          time: b.time as UTCTimestamp,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
        }))
      );

      // ── FVG zones (top + bottom price lines) ─────────────────
      for (const fvg of fvgZones.slice(-50)) {
        if (fvg.filled) continue;
        const bull = fvg.fvg_type === "bullish";
        const alpha = TF_ALPHA[fvg.timeframe] ?? 0.55;
        const color = bull
          ? `rgba(38,166,154,${alpha})`
          : `rgba(239,83,80,${alpha})`;
        const tf = TF_LABEL[fvg.timeframe] ?? fvg.timeframe.toUpperCase();
        const label = `${tf} ${bull ? "BFVG" : "BRVG"}`;

        candles.createPriceLine({
          price: fvg.high,
          color,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: false,
          title: label,
        });
        candles.createPriceLine({
          price: fvg.low,
          color,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: false,
          title: "",
        });
      }

      // ── Liquidity levels ─────────────────────────────────────
      for (const liq of liquidityLevels.slice(-20)) {
        const color = LIQ_COLOR[liq.level_type] ?? "#546E7A";
        const swept = liq.swept ?? false;
        candles.createPriceLine({
          price: liq.price,
          color: swept ? "#546E7A" : color,
          lineWidth: swept ? 1 : 2,
          lineStyle: swept ? LineStyle.Dotted : LineStyle.Solid,
          axisLabelVisible: true,
          title: `${liq.level_type}${swept ? " ✓" : ""}`,
        });
      }

      // ── Trade + sweep markers ─────────────────────────────────
      type Marker = {
        time: UTCTimestamp;
        position: "aboveBar" | "belowBar" | "inBar";
        shape: "circle" | "square" | "arrowUp" | "arrowDown";
        color: string;
        text?: string;
        size?: number;
      };
      const markers: Marker[] = [];

      for (const t of trades) {
        const long = t.direction === "long";
        const win = t.pnl_net > 0;
        const entryTs = toTs(new Date(t.entry_time).getTime());
        const exitTs = toTs(new Date(t.exit_time).getTime());

        markers.push({
          time: entryTs,
          position: long ? "belowBar" : "aboveBar",
          shape: long ? "arrowUp" : "arrowDown",
          color: long ? "#26a69a" : "#ef5350",
          text: `${long ? "L" : "S"} @${t.entry_price.toFixed(0)}`,
          size: 2,
        });
        markers.push({
          time: exitTs,
          // Win exits in the "good" direction, loss exits where the SL was hit:
          // LONG win → above bar (price went up), LONG loss → below bar (SL below)
          // SHORT win → below bar (price went down), SHORT loss → above bar (SL above)
          position: (long === win) ? "aboveBar" : "belowBar",
          shape: win ? "circle" : "square",
          color: win ? "#26a69a" : "#ef5350",
          text: `${win ? "+" : ""}${t.pnl_net.toFixed(0)}`,
          size: 1.5,
        });
      }

      for (const sw of sweeps) {
        const buyside = sw.sweep_type === "buyside";
        markers.push({
          time: toTs(new Date(sw.timestamp).getTime()),
          position: buyside ? "aboveBar" : "belowBar",
          shape: buyside ? "arrowDown" : "arrowUp",
          color: "#FF9800",
          text: buyside ? "BSL" : "SSL",
          size: 1,
        });
      }

      markers.sort((a, b) => a.time - b.time);
      if (markers.length > 0) {
        candles.setMarkers(markers);
      }

      chart.timeScale().fitContent();

      // ── Responsive resize ─────────────────────────────────────
      resizeObs = new ResizeObserver(() => {
        if (containerRef.current && chartInst) {
          chartInst.applyOptions({ width: containerRef.current.clientWidth });
        }
      });
      resizeObs.observe(containerRef.current!);
    });

    return () => {
      destroyed = true;
      resizeObs?.disconnect();
      chartInst?.remove();
    };
  }, [activeOhlc, trades, fvgZones, liquidityLevels, sweeps, height]);

  if (activeOhlc.length === 0) {
    return (
      <div
        style={{ height }}
        className="flex flex-col items-center justify-center gap-2 text-text-secondary"
      >
        <p className="text-sm">Sin datos OHLC disponibles</p>
        <p className="text-xs text-text-muted">
          Ejecuta un backtest para ver el gráfico de velas
        </p>
      </div>
    );
  }

  return (
    <div className="w-full">
      {availableTfs.length > 1 && (
        <div className="flex items-center gap-1 mb-2">
          <span className="text-xs text-text-muted mr-1">TF:</span>
          {availableTfs.map((tf) => (
            <button
              key={tf}
              onClick={() => setSelectedTf(tf)}
              className={cn(
                "px-2 py-0.5 rounded text-xs font-mono transition-colors",
                selectedTf === tf
                  ? "bg-brand-blue text-white"
                  : "bg-bg-tertiary text-text-secondary hover:text-text-primary border border-border"
              )}
            >
              {TF_LABEL[tf] ?? tf.toUpperCase()}
            </button>
          ))}
        </div>
      )}
      <div ref={containerRef} className="w-full rounded overflow-hidden" style={{ height }} />
    </div>
  );
}
