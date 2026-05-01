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

export function generateMockTrades(count = 38): Trade[] {
  const trades: Trade[] = [];
  const startDate = new Date("2025-10-01T09:30:00");
  let equity = 50000;

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

  let d = new Date(startDate);
  for (let i = 0; i < count; i++) {
    d = new Date(d.getTime() + randomBetween(1, 3) * 24 * 3600 * 1000);
    if (d.getDay() === 0) d = new Date(d.getTime() + 24 * 3600 * 1000);
    if (d.getDay() === 6) d = new Date(d.getTime() + 2 * 24 * 3600 * 1000);

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
    equity += pnlNet;

    const entryTime = new Date(d);
    entryTime.setHours(9, 30 + Math.floor(randomBetween(0, 90)), 0, 0);
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
  }
  return trades;
}

export function buildEquityCurve(
  trades: Trade[],
  initial = 50000
): EquityPoint[] {
  let equity = initial;
  let peak = initial;
  const points: EquityPoint[] = [
    {
      datetime: new Date("2025-10-01").toISOString(),
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
  const mean = totalPnl / trades.length;
  const variance =
    pnls.reduce((s, p) => s + Math.pow(p - mean, 2), 0) / pnls.length;
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

export function generateMockOHLC(bars = 600, barSec = 3600): OHLCBar[] {
  const result: OHLCBar[] = [];
  let price = 19800;
  let time = Math.floor(new Date("2025-10-01T09:30:00Z").getTime() / 1000);

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

const TF_OHLC_CONFIG: Record<string, [number, number]> = {
  "4h": [250, 14400],
  "1h": [600, 3600],
  "15m": [800, 900],
  "5m": [1000, 300],
  "1m": [600, 60],
};

export function generateMockOHLCByTimeframe(): Record<string, OHLCBar[]> {
  return Object.fromEntries(
    Object.entries(TF_OHLC_CONFIG).map(([tf, [bars, sec]]) => [
      tf,
      generateMockOHLC(bars, sec),
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

export function generateMockSweeps(): SweepEvent[] {
  const sweeps: SweepEvent[] = [];
  let d = new Date("2025-10-06T14:00:00Z");
  for (let i = 0; i < 10; i++) {
    d = new Date(d.getTime() + randomBetween(2, 6) * 24 * 3600 * 1000);
    const buyside = Math.random() > 0.5;
    sweeps.push({
      price: +(19800 + (buyside ? 200 : -200) + randomBetween(-80, 80)).toFixed(2),
      sweep_type: buyside ? "buyside" : "sellside",
      timestamp: d.toISOString(),
      timeframe: ["1h", "15m", "4h"][Math.floor(Math.random() * 3)],
    });
  }
  return sweeps;
}

const MOCK_TRADES = generateMockTrades(38);
const MOCK_CURVE = buildEquityCurve(MOCK_TRADES);
const MOCK_METRICS = computeMockMetrics(MOCK_TRADES);

export const MOCK_BACKTEST_RESULT: BacktestResult = {
  backtest_id: "mock-001",
  metrics: MOCK_METRICS,
  trades: MOCK_TRADES,
  equity_curve: MOCK_CURVE,
  config: DEFAULT_CONFIG,
  fvg_summary: MOCK_FVG_SUMMARY,
  period_name: "Oct–Nov 2025",
  ohlc_data: generateMockOHLC(600),
  ohlc_by_timeframe: generateMockOHLCByTimeframe(),
  fvg_zones: generateMockFVGZones(),
  liquidity_levels: generateMockLiquidityLevels(),
  sweeps: generateMockSweeps(),
};
