import type {
  BacktestResult,
  Trade,
  EquityPoint,
  PerformanceMetrics,
  BotConfig,
  FVGSummary,
  OHLCBar,
  FVGZone,
  LiquidityLevel,
  SweepEvent,
} from "./types";

export const DEFAULT_CONFIG: BotConfig = {
  name: "Moderado",
  initial_capital: 50000,
  max_daily_loss: 550,
  max_trades_per_day: 2,
  default_contracts: 3,
  big_loss_threshold: 400,
  big_win_threshold: 800,
  fvg_lookback_1h: 10,
  fvg_lookback_15m: 16,
  fvg_lookback_5m: 24,
  fvg_lookback_1m: 30,
  fvg_max_1h: 4,
  fvg_max_15m: 4,
  fvg_max_5m: 3,
  fvg_max_1m: 3,
  fvg_search_range: 300,
  structure_lookback: 6,
  break_even_pct: 0.6,
  close_at_pct: 0.9,
};

export const PRESET_CONFIGS: Record<string, BotConfig> = {
  Conservador: {
    ...DEFAULT_CONFIG,
    name: "Conservador",
    max_daily_loss: 400,
    default_contracts: 2,
    big_loss_threshold: 300,
    big_win_threshold: 600,
    break_even_pct: 0.5,
    close_at_pct: 0.85,
  },
  Moderado: DEFAULT_CONFIG,
  Agresivo: {
    ...DEFAULT_CONFIG,
    name: "Agresivo",
    max_daily_loss: 750,
    default_contracts: 4,
    big_loss_threshold: 500,
    big_win_threshold: 1000,
    break_even_pct: 0.65,
    close_at_pct: 0.95,
  },
};

function randomBetween(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

const MS_PER_DAY = 24 * 3600 * 1000;

function nextWeekday(d: Date): Date {
  const day = d.getUTCDay();
  if (day === 6) return new Date(d.getTime() + 2 * MS_PER_DAY);
  if (day === 0) return new Date(d.getTime() + MS_PER_DAY);
  return d;
}

export function generateMockTrades(
  startDate = "2025-10-01",
  endDate = "2025-11-30"
): Trade[] {
  const start = new Date(startDate + "T00:00:00Z");
  const end = new Date(endDate + "T23:59:59Z");

  const totalDays = Math.max(1, (end.getTime() - start.getTime()) / MS_PER_DAY);
  const tradingDays = Math.round(totalDays * 5 / 7);
  // ~0.55 trades per trading day, clamp to [3, 200]
  const count = Math.max(3, Math.min(200, Math.round(tradingDays * 0.55)));

  const exitReasons = [
    "TP Hit",
    "90% TP",
    "SL Hit",
    "Break Even",
    "Forced Close (VET 4PM)",
    "Session Close (NY Lunch)",
    "FVG Protector Roto",
  ];
  const reasonWeights = [25, 30, 20, 10, 5, 5, 5];

  function pickReason(): string {
    const total = reasonWeights.reduce((a, b) => a + b, 0);
    let r = Math.random() * total;
    for (let i = 0; i < exitReasons.length; i++) {
      r -= reasonWeights[i];
      if (r <= 0) return exitReasons[i];
    }
    return exitReasons[0];
  }

  const trades: Trade[] = [];
  // Spread trades evenly, with jitter
  const step = (end.getTime() - start.getTime()) / count;
  let d = nextWeekday(new Date(start.getTime() + randomBetween(0, step * 0.5)));

  for (let i = 0; i < count; i++) {
    d = nextWeekday(d);
    if (d > end) break;

    const dir: "long" | "short" = Math.random() > 0.45 ? "long" : "short";
    const basePrice = 19800 + randomBetween(-500, 500);
    const slDist = randomBetween(15, 60);
    const tpDist = slDist * randomBetween(1.2, 2.8);
    const contracts = Math.floor(randomBetween(2, 5));

    const slPrice = dir === "long" ? basePrice - slDist : basePrice + slDist;
    const tpPrice = dir === "long" ? basePrice + tpDist : basePrice - tpDist;

    const isWin = Math.random() < 0.55;
    const reason = pickReason();
    let exitPrice: number;
    if (reason === "SL Hit") {
      exitPrice = slPrice + randomBetween(-2, 2);
    } else if (reason === "TP Hit") {
      exitPrice = tpPrice + randomBetween(-2, 2);
    } else {
      const pct = randomBetween(0.5, 1.0);
      exitPrice =
        dir === "long"
          ? basePrice + tpDist * pct * (isWin ? 1 : -0.3)
          : basePrice - tpDist * pct * (isWin ? 1 : -0.3);
    }

    const pnlGross =
      (dir === "long" ? exitPrice - basePrice : basePrice - exitPrice) *
      contracts *
      2;
    const commission = contracts * 2 * 0.62 + contracts * 2 * 0.5;
    const pnlNet = pnlGross - commission;

    const entryTime = new Date(d);
    entryTime.setUTCHours(9, 30 + Math.floor(randomBetween(0, 90)), 0, 0);
    const exitTime = new Date(
      entryTime.getTime() + randomBetween(15, 120) * 60 * 1000
    );

    trades.push({
      id: `trade-${i}`,
      timestamp: entryTime.toISOString(),
      entry_time: entryTime.toISOString(),
      exit_time: exitTime.toISOString(),
      direction: dir,
      entry_price: basePrice,
      exit_price: exitPrice,
      sl_price: slPrice,
      tp_price: tpPrice,
      pnl_gross: pnlGross,
      pnl_net: pnlNet,
      commission,
      contracts,
      reason,
    });

    // Advance cursor with jitter
    d = new Date(
      d.getTime() + step + randomBetween(-step * 0.3, step * 0.3)
    );
  }

  return trades.sort(
    (a, b) =>
      new Date(a.entry_time).getTime() - new Date(b.entry_time).getTime()
  );
}

export function buildEquityCurve(
  trades: Trade[],
  initial = 50000,
  startDate?: string
): EquityPoint[] {
  let equity = initial;
  let peak = initial;
  const firstDate =
    startDate
      ? new Date(startDate).toISOString()
      : trades[0]?.entry_time ?? new Date().toISOString();

  const points: EquityPoint[] = [
    {
      datetime: firstDate,
      equity: initial,
      pnl: 0,
      drawdown: 0,
      drawdown_pct: 0,
    },
  ];

  for (const t of trades) {
    equity += t.pnl_net;
    peak = Math.max(peak, equity);
    const dd = peak - equity;
    points.push({
      datetime: t.exit_time,
      equity,
      pnl: t.pnl_net,
      drawdown: dd,
      drawdown_pct: dd / peak,
    });
  }
  return points;
}

export function computeMockMetrics(
  trades: Trade[],
  initialBalance = 50000
): PerformanceMetrics {
  const wins = trades.filter((t) => t.pnl_net > 0);
  const losses = trades.filter((t) => t.pnl_net <= 0);
  const totalPnl = trades.reduce((s, t) => s + t.pnl_net, 0);
  const totalGross = trades.reduce((s, t) => s + t.pnl_gross, 0);
  const totalComm = trades.reduce((s, t) => s + t.commission, 0);
  const winSum = wins.reduce((s, t) => s + t.pnl_net, 0);
  const lossSum = Math.abs(losses.reduce((s, t) => s + t.pnl_net, 0));
  const winRate = trades.length > 0 ? wins.length / trades.length : 0;
  const avgWin = wins.length > 0 ? winSum / wins.length : 0;
  const avgLoss = losses.length > 0 ? lossSum / losses.length : 0;
  const profitFactor = lossSum > 0 ? winSum / lossSum : 0;
  const expectancy = trades.length > 0 ? totalPnl / trades.length : 0;

  const curve = buildEquityCurve(trades, initialBalance);
  const maxDD = Math.max(...curve.map((p) => p.drawdown));
  const maxDDPct = maxDD / initialBalance;

  const dailyMap = new Map<string, number>();
  for (const t of trades) {
    const date = t.entry_time.slice(0, 10);
    dailyMap.set(date, (dailyMap.get(date) ?? 0) + t.pnl_net);
  }
  const dailyVals = Array.from(dailyMap.values());
  const bestDay = Math.max(...dailyVals, 0);
  const worstDay = Math.min(...dailyVals, 0);

  const pnls = trades.map((t) => t.pnl_net);
  const mean = trades.length > 0 ? totalPnl / trades.length : 0;
  const variance =
    pnls.length > 0
      ? pnls.reduce((s, p) => s + Math.pow(p - mean, 2), 0) / pnls.length
      : 0;
  const sharpe = variance > 0 ? mean / Math.sqrt(variance) : 0;

  const days =
    (new Date(trades[trades.length - 1]?.exit_time ?? Date.now()).getTime() -
      new Date(trades[0]?.entry_time ?? Date.now()).getTime()) /
    (1000 * 3600 * 24);

  return {
    total_trades: trades.length,
    winning_trades: wins.length,
    losing_trades: losses.length,
    win_rate: winRate,
    profit_factor: profitFactor,
    total_pnl: totalPnl,
    total_pnl_gross: totalGross,
    total_commission: totalComm,
    initial_balance: initialBalance,
    final_balance: initialBalance + totalPnl,
    total_return_pct: totalPnl / initialBalance,
    avg_win: avgWin,
    avg_loss: avgLoss,
    expectancy,
    largest_win: Math.max(...wins.map((t) => t.pnl_net), 0),
    largest_loss: Math.min(...losses.map((t) => t.pnl_net), 0),
    max_drawdown_usd: maxDD,
    max_drawdown_pct: maxDDPct,
    max_drawdown_duration_days: 5,
    avg_drawdown_usd: maxDD * 0.4,
    best_day_pnl: bestDay,
    worst_day_pnl: worstDay,
    sharpe_ratio: sharpe * Math.sqrt(252),
    sortino_ratio: sharpe * Math.sqrt(252) * 1.2,
    avg_rr_ratio: 1.65,
    trades_per_day: days > 0 ? trades.length / days : 0,
    avg_trade_duration_hours: 1.2,
    consistency_check_passed: true,
  };
}

export const MOCK_FVG_SUMMARY: FVGSummary[] = [
  { timeframe: "1h", total: 12, bullish: 7, bearish: 5, decision: 4, avg_confluence: 3.2 },
  { timeframe: "15m", total: 28, bullish: 16, bearish: 12, decision: 9, avg_confluence: 2.1 },
  { timeframe: "5m", total: 45, bullish: 24, bearish: 21, decision: 12, avg_confluence: 1.4 },
  { timeframe: "1m", total: 87, bullish: 46, bearish: 41, decision: 18, avg_confluence: 0.9 },
];

// barSec: seconds per candle. Bar count is derived from the date range, capped at 2000.
export function generateMockOHLC(
  startDate = "2025-10-01",
  endDate = "2025-11-30",
  barSec = 3600
): OHLCBar[] {
  const startTs = Math.floor(
    new Date(startDate + "T09:30:00Z").getTime() / 1000
  );
  const endTs = Math.floor(
    new Date(endDate + "T16:00:00Z").getTime() / 1000
  );
  const totalSec = Math.max(barSec, endTs - startTs);
  const bars = Math.min(Math.ceil(totalSec / barSec), 2000);

  const result: OHLCBar[] = [];
  let price = 19800;
  let time = startTs;

  for (let i = 0; i < bars; i++) {
    const trend = Math.sin(i / 80) * 150;
    const change = randomBetween(-55, 55) + trend * 0.015;
    const open = price;
    const close = price + change;
    const high = Math.max(open, close) + randomBetween(4, 28);
    const low = Math.min(open, close) - randomBetween(4, 28);
    result.push({
      time,
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +close.toFixed(2),
      volume: Math.floor(randomBetween(800, 9000)),
    });
    price = close;
    time += barSec;
  }
  return result;
}

const TF_BAR_SEC: Record<string, number> = {
  "4h": 14400,
  "1h": 3600,
  "15m": 900,
  "5m": 300,
  "1m": 60,
};

export function generateMockOHLCByTimeframe(
  startDate = "2025-10-01",
  endDate = "2025-11-30"
): Record<string, OHLCBar[]> {
  return Object.fromEntries(
    Object.entries(TF_BAR_SEC).map(([tf, sec]) => [
      tf,
      generateMockOHLC(startDate, endDate, sec),
    ])
  );
}

export function generateMockFVGZones(): FVGZone[] {
  const zones: FVGZone[] = [];
  const tfs: Array<[string, number]> = [["4h", 2], ["1h", 5], ["15m", 8], ["5m", 6]];
  const basePrice = 19800;

  for (const [tf, count] of tfs) {
    for (let i = 0; i < count; i++) {
      const mid = basePrice + randomBetween(-700, 700);
      const gap = randomBetween(8, 55);
      const isBull = Math.random() > 0.48;
      zones.push({
        fvg_type: isBull ? "bullish" : "bearish",
        timeframe: tf,
        high: +(mid + gap / 2).toFixed(2),
        low: +(mid - gap / 2).toFixed(2),
        filled: Math.random() < 0.25,
      });
    }
  }
  return zones;
}

export function generateMockLiquidityLevels(): LiquidityLevel[] {
  const base = 19800;
  const levels: Array<[string, number]> = [
    ["PDH", 305], ["PDL", -288], ["EQH", 162], ["EQL", -155],
    ["ATH", 618], ["ATL", -572], ["swing_high", 88],
    ["swing_high", 234], ["swing_low", -95], ["swing_low", -210],
  ];
  return levels.map(([type, offset]) => ({
    price: +(base + offset + randomBetween(-15, 15)).toFixed(2),
    level_type: type,
    swept: Math.random() < 0.28,
  }));
}

export function generateMockSweeps(
  startDate = "2025-10-01",
  endDate = "2025-11-30"
): SweepEvent[] {
  const sweeps: SweepEvent[] = [];
  const start = new Date(startDate + "T09:00:00Z");
  const end = new Date(endDate + "T16:00:00Z");
  const range = Math.max(MS_PER_DAY, end.getTime() - start.getTime());

  const count = Math.max(3, Math.min(20, Math.floor(range / (3 * MS_PER_DAY))));
  const step = range / count;
  let d = new Date(start.getTime() + randomBetween(0, step * 0.5));

  for (let i = 0; i < count; i++) {
    if (d > end) break;
    const buyside = Math.random() > 0.5;
    sweeps.push({
      price: +(19800 + (buyside ? 200 : -200) + randomBetween(-80, 80)).toFixed(2),
      sweep_type: buyside ? "buyside" : "sellside",
      timestamp: d.toISOString(),
      timeframe: ["1h", "15m", "4h"][Math.floor(Math.random() * 3)],
    });
    d = new Date(
      d.getTime() + step + randomBetween(-step * 0.2, step * 0.2)
    );
  }
  return sweeps;
}

export function generateMockBacktestResult(
  startDate: string,
  endDate: string,
  interval = "1h"
): BacktestResult {
  const barSec = TF_BAR_SEC[interval] ?? 3600;
  const trades = generateMockTrades(startDate, endDate);
  const equity_curve = buildEquityCurve(trades, 50000, startDate);
  const metrics = computeMockMetrics(trades);

  return {
    backtest_id: `mock-${startDate}-${endDate}`,
    metrics,
    trades,
    equity_curve,
    config: DEFAULT_CONFIG,
    fvg_summary: MOCK_FVG_SUMMARY,
    period_name: `${startDate} → ${endDate}`,
    ohlc_data: generateMockOHLC(startDate, endDate, barSec),
    ohlc_by_timeframe: generateMockOHLCByTimeframe(startDate, endDate),
    fvg_zones: generateMockFVGZones(),
    liquidity_levels: generateMockLiquidityLevels(),
    sweeps: generateMockSweeps(startDate, endDate),
  };
}

// Static fallback used for initial page load before any backtest is run
export const MOCK_BACKTEST_RESULT: BacktestResult = generateMockBacktestResult(
  "2025-10-01",
  "2025-11-30"
);
