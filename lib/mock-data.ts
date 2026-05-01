import type {
  BacktestResult,
  Trade,
  TradeContext,
  TradeSetupCondition,
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

// ── Seeded PRNG (Mulberry32) ─────────────────────────────────────────────
// Replaces Math.random() so that identical params → identical results.
type RandFn = () => number;

function createSeededRand(seed: number): RandFn {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 0x100000000;
  };
}

function between(rand: RandFn, min: number, max: number): number {
  return rand() * (max - min) + min;
}

// FNV-1a hash → deterministic integer seed from the run parameters
function paramSeed(
  startDate: string,
  endDate: string,
  interval: string,
  cfg: BotConfig
): number {
  const key = [
    startDate,
    endDate,
    interval,
    cfg.default_contracts,
    cfg.initial_capital,
    cfg.max_daily_loss,
    cfg.max_trades_per_day,
  ].join("|");
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) {
    h = Math.imul(h ^ key.charCodeAt(i), 16777619);
  }
  return h >>> 0;
}

const MS_PER_DAY = 24 * 3600 * 1000;

function nextWeekday(d: Date): Date {
  const day = d.getUTCDay();
  if (day === 6) return new Date(d.getTime() + 2 * MS_PER_DAY);
  if (day === 0) return new Date(d.getTime() + MS_PER_DAY);
  return d;
}

// ── Trade context generator ──────────────────────────────────────────────
// Builds the rich "why did the bot take this trade / how did it exit" context
// that is displayed in the trade journal.
function generateTradeContext(
  trade: Omit<Trade, "context">,
  rand: RandFn
): TradeContext {
  const entryHour = new Date(trade.entry_time).getUTCHours();

  // Killzone classification by UTC hour
  let killzone: string;
  if (entryHour >= 2 && entryHour < 5)        killzone = "London Open";
  else if (entryHour >= 7 && entryHour < 9)   killzone = "London/NY Overlap";
  else if (entryHour >= 13 && entryHour < 16) killzone = "NY Open";
  else if (entryHour >= 19 && entryHour < 21) killzone = "NY Afternoon";
  else                                          killzone = "Off-Session";

  const market_structure: TradeContext["market_structure"] =
    trade.direction === "long"
      ? (rand() > 0.2 ? "bullish" : "ranging")
      : (rand() > 0.2 ? "bearish" : "ranging");

  const zoneOptions: TradeContext["price_zone"][] = ["discount", "premium", "equilibrium"];
  const price_zone = zoneOptions[Math.floor(rand() * 3)];

  const tfOptions = ["1h", "15m", "5m", "1m"];
  const trigger_fvg_timeframe = tfOptions[Math.floor(rand() * tfOptions.length)];
  const trigger_fvg_type: TradeContext["trigger_fvg_type"] =
    trade.direction === "long" ? "bullish" : "bearish";
  const trigger_fvg_size_points = +between(rand, 5, 35).toFixed(1);

  const confCount = Math.floor(rand() * 4);
  const fvg_confluence = Array.from({ length: confCount }, () => ({
    timeframe: tfOptions[Math.floor(rand() * tfOptions.length)],
    type: (rand() > 0.3
      ? trigger_fvg_type
      : trigger_fvg_type === "bullish" ? "bearish" : "bullish") as TradeContext["trigger_fvg_type"],
  }));

  const targetLabels = ["PDH", "PDL", "EQH", "EQL", "ATH", "ATL", "Swing High", "Swing Low"];
  const nearest_target = targetLabels[Math.floor(rand() * targetLabels.length)];

  const sweepLabels = ["Buyside Sweep", "Sellside Sweep"];
  const recent_sweep = rand() > 0.35 ? sweepLabels[Math.floor(rand() * 2)] : null;

  const targetDist = +between(rand, 15, 80).toFixed(0);
  const liqPassed = rand() > 0.25;
  const killzonePassed = killzone !== "Off-Session";

  const conditions: TradeSetupCondition[] = [
    {
      label: "Estructura de mercado",
      detail:
        market_structure === "bullish" ? "Break of structure alcista confirmado en 1H" :
        market_structure === "bearish" ? "Break of structure bajista confirmado en 1H" :
        "Sin estructura clara — mercado en rango",
      score: 2,
      passed: market_structure !== "ranging",
    },
    {
      label: "FVG disparador",
      detail: `FVG ${trigger_fvg_type === "bullish" ? "alcista" : "bajista"} de ${trigger_fvg_size_points} pts en ${trigger_fvg_timeframe.toUpperCase()} detectado`,
      score: 2,
      passed: true,
    },
    {
      label: "Confluencia de FVGs",
      detail:
        confCount > 0
          ? `${confCount} FVG(s) alineado(s) en ${fvg_confluence.map((f) => f.timeframe).join(", ")}`
          : "Sin FVGs adicionales de confluencia",
      score: 2,
      passed: confCount > 0,
    },
    {
      label: "Zona de precio",
      detail:
        price_zone === "discount" ? "Precio en zona de descuento — favorable para largos" :
        price_zone === "premium"  ? "Precio en zona de prima — favorable para cortos" :
        "Precio en equilibrio — zona neutral",
      score: 1,
      passed:
        (price_zone === "discount" && trade.direction === "long") ||
        (price_zone === "premium"  && trade.direction === "short"),
    },
    {
      label: "Objetivo de liquidez",
      detail: `${nearest_target} identificado como target a ${targetDist} pts`,
      score: 1,
      passed: liqPassed,
    },
    {
      label: "Sweep reciente",
      detail: recent_sweep
        ? `${recent_sweep} detectado — reposicionamiento de smart money`
        : "Sin sweep reciente — setup más débil sin confirmación",
      score: 1,
      passed: recent_sweep !== null,
    },
    {
      label: "Killzone de entrada",
      detail: `Entrada durante ${killzone}`,
      score: 1,
      passed: killzonePassed,
    },
  ];

  const setup_score = conditions.reduce((s, c) => s + (c.passed ? c.score : 0), 0);
  const min_score = 6;

  const slDist = Math.abs(trade.entry_price - trade.sl_price).toFixed(1);
  let exit_detail: string;
  if (trade.reason === "TP Hit") {
    exit_detail = `TP completo alcanzado en ${trade.exit_price.toFixed(2)}. Objetivo original: ${trade.tp_price.toFixed(2)}.`;
  } else if (trade.reason === "90% TP") {
    exit_detail = `Posición cerrada al 90% del objetivo (${trade.exit_price.toFixed(2)}) por regla close_at_pct.`;
  } else if (trade.reason === "SL Hit") {
    exit_detail = `Stop loss activado en ${trade.exit_price.toFixed(2)}. Riesgo contenido en ${slDist} pts.`;
  } else if (trade.reason === "Break Even") {
    exit_detail = `Trade movido a break-even y salida plana. FVG protector posiblemente invalidado.`;
  } else {
    exit_detail = `${trade.reason}: posición cerrada por reglas de sesión en ${trade.exit_price.toFixed(2)}.`;
  }

  return {
    market_structure,
    price_zone,
    killzone,
    trigger_fvg_timeframe,
    trigger_fvg_type,
    trigger_fvg_size_points,
    fvg_confluence,
    nearest_target,
    recent_sweep,
    setup_score,
    min_score,
    conditions,
    exit_detail,
  };
}

// ── Trade generator ──────────────────────────────────────────────────────
// Respects: default_contracts, max_trades_per_day, max_daily_loss, initial_capital
export function generateMockTrades(
  startDate = "2025-10-01",
  endDate = "2025-11-30",
  config: BotConfig = DEFAULT_CONFIG,
  rand: RandFn = Math.random
): Trade[] {
  const start = new Date(startDate + "T00:00:00Z");
  const end = new Date(endDate + "T23:59:59Z");

  const totalDays = Math.max(1, (end.getTime() - start.getTime()) / MS_PER_DAY);
  const tradingDays = Math.round((totalDays * 5) / 7);
  // ~0.55 target trades per trading day, but capped by max_trades_per_day ceiling
  const targetCount = Math.max(3, Math.min(200, Math.round(tradingDays * 0.55)));

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
    let r = rand() * total;
    for (let i = 0; i < exitReasons.length; i++) {
      r -= reasonWeights[i];
      if (r <= 0) return exitReasons[i];
    }
    return exitReasons[0];
  }

  const trades: Trade[] = [];
  const dailyCount = new Map<string, number>();
  const dailyPnl = new Map<string, number>();

  // ── Prop-firm trailing drawdown guard (OneUpTrader rules) ────────────
  // Hard limit: 5 % of initial capital (MAX_DD_USD).
  // The floor trails the running peak by MAX_DD_USD UNTIL the peak crosses
  // initial_capital + MAX_DD_USD; from that point on the floor LOCKS at
  // initial_capital — once the trader has secured the buffer, the floor
  // never moves above the starting balance no matter how high equity goes.
  //   floor = min(peak − MAX_DD_USD, initial_capital)
  // Buffer-from-floor (as % of MAX_DD_USD consumed) drives contract sizing:
  //   < 60 % consumed → full size  (config.default_contracts)
  //   60–80 % consumed → half size (ceil(default / 2), min 1)
  //   80–100 % consumed → minimum  (1 contract)
  //   ≥ 100 % consumed → stop trading (equity at/below floor → blown)
  const MAX_DD_USD = config.initial_capital * 0.05;
  let equity = config.initial_capital;
  let peakEquity = config.initial_capital;
  let floor = config.initial_capital - MAX_DD_USD;

  const step = (end.getTime() - start.getTime()) / targetCount;
  let d = nextWeekday(
    new Date(start.getTime() + between(rand, 0, step * 0.5))
  );

  for (let i = 0; i < targetCount; i++) {
    d = nextWeekday(d);
    if (d > end) break;

    const dateKey = d.toISOString().slice(0, 10);

    // ── Kill switch: equity reached the trailing floor ────────────
    // ddRatio = fraction of the MAX_DD_USD buffer already consumed.
    //   0 = full buffer (equity is MAX_DD_USD above floor or higher)
    //   1 = at floor → account blown.
    // Negative values (equity > floor + MAX_DD_USD, only possible after the
    // floor locks at initial_capital) are clamped to 0 — full safe zone.
    const buffer = equity - floor;
    const ddRatio = Math.max(0, 1 - buffer / MAX_DD_USD);
    if (ddRatio >= 1.0) break;

    // ── Kill switch: max trades per day ───────────────────────────
    if ((dailyCount.get(dateKey) ?? 0) >= config.max_trades_per_day) {
      d = nextWeekday(new Date(d.getTime() + MS_PER_DAY));
      d.setUTCHours(9, 30, 0, 0);
      d = new Date(d.getTime() + between(rand, 0, step * 0.3));
      continue;
    }

    // ── Kill switch: daily loss limit ─────────────────────────────
    if ((dailyPnl.get(dateKey) ?? 0) <= -config.max_daily_loss) {
      d = nextWeekday(new Date(d.getTime() + MS_PER_DAY));
      d.setUTCHours(9, 30, 0, 0);
      d = new Date(d.getTime() + between(rand, 0, step * 0.3));
      continue;
    }

    // ── Dynamic contract sizing based on DD proximity ─────────────
    let contracts: number;
    if (ddRatio < 0.6) {
      contracts = config.default_contracts;                          // safe zone
    } else if (ddRatio < 0.8) {
      contracts = Math.max(1, Math.ceil(config.default_contracts / 2)); // caution
    } else {
      contracts = 1;                                                 // danger zone
    }

    // ── Trade parameters ──────────────────────────────────────────
    const dir: "long" | "short" = rand() > 0.45 ? "long" : "short";
    const basePrice = 19800 + between(rand, -500, 500);
    const slDist = between(rand, 15, 60);
    const tpDist = slDist * between(rand, 1.2, 2.8);

    const slPrice = dir === "long" ? basePrice - slDist : basePrice + slDist;
    const tpPrice = dir === "long" ? basePrice + tpDist : basePrice - tpDist;

    const isWin = rand() < 0.55;
    const reason = pickReason();
    let exitPrice: number;
    if (reason === "SL Hit") {
      exitPrice = slPrice + between(rand, -2, 2);
    } else if (reason === "TP Hit") {
      exitPrice = tpPrice + between(rand, -2, 2);
    } else {
      const pct = between(rand, 0.5, 1.0);
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

    // Update daily tracking and running equity (used for DD guard next iteration)
    dailyCount.set(dateKey, (dailyCount.get(dateKey) ?? 0) + 1);
    dailyPnl.set(dateKey, (dailyPnl.get(dateKey) ?? 0) + pnlNet);
    equity += pnlNet;
    if (equity > peakEquity) {
      peakEquity = equity;
      // Floor trails peak by MAX_DD_USD; once peak ≥ initial + MAX_DD_USD,
      // the formula caps the floor at initial_capital (locked forever).
      floor = Math.min(peakEquity - MAX_DD_USD, config.initial_capital);
    }

    const entryTime = new Date(d);
    entryTime.setUTCHours(9, 30 + Math.floor(between(rand, 0, 90)), 0, 0);
    const exitTime = new Date(
      entryTime.getTime() + between(rand, 15, 120) * 60 * 1000
    );

    const tradeBase = {
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
    };
    trades.push({ ...tradeBase, context: generateTradeContext(tradeBase, rand) });

    d = new Date(
      d.getTime() + step + between(rand, -step * 0.3, step * 0.3)
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
    { datetime: firstDate, equity: initial, pnl: 0, drawdown: 0, drawdown_pct: 0 },
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
  { timeframe: "1h",  total: 12, bullish: 7,  bearish: 5,  decision: 4,  avg_confluence: 3.2 },
  { timeframe: "15m", total: 28, bullish: 16, bearish: 12, decision: 9,  avg_confluence: 2.1 },
  { timeframe: "5m",  total: 45, bullish: 24, bearish: 21, decision: 12, avg_confluence: 1.4 },
  { timeframe: "1m",  total: 87, bullish: 46, bearish: 41, decision: 18, avg_confluence: 0.9 },
];

// ── OHLC generator (seeded) ──────────────────────────────────────────────
export function generateMockOHLC(
  startDate = "2025-10-01",
  endDate = "2025-11-30",
  barSec = 3600,
  rand: RandFn = Math.random
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
    const change = between(rand, -55, 55) + trend * 0.015;
    const open = price;
    const close = price + change;
    const high = Math.max(open, close) + between(rand, 4, 28);
    const low = Math.min(open, close) - between(rand, 4, 28);
    result.push({
      time,
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +close.toFixed(2),
      volume: Math.floor(between(rand, 800, 9000)),
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
  endDate = "2025-11-30",
  rand: RandFn = Math.random
): Record<string, OHLCBar[]> {
  return Object.fromEntries(
    Object.entries(TF_BAR_SEC).map(([tf, sec]) => [
      tf,
      generateMockOHLC(startDate, endDate, sec, rand),
    ])
  );
}

export function generateMockFVGZones(rand: RandFn = Math.random): FVGZone[] {
  const zones: FVGZone[] = [];
  const tfs: Array<[string, number]> = [
    ["4h", 2], ["1h", 5], ["15m", 8], ["5m", 6],
  ];
  const basePrice = 19800;
  for (const [tf, count] of tfs) {
    for (let i = 0; i < count; i++) {
      const mid = basePrice + between(rand, -700, 700);
      const gap = between(rand, 8, 55);
      const isBull = rand() > 0.48;
      zones.push({
        fvg_type: isBull ? "bullish" : "bearish",
        timeframe: tf,
        high: +(mid + gap / 2).toFixed(2),
        low: +(mid - gap / 2).toFixed(2),
        filled: rand() < 0.25,
      });
    }
  }
  return zones;
}

export function generateMockLiquidityLevels(
  rand: RandFn = Math.random
): LiquidityLevel[] {
  const base = 19800;
  const levels: Array<[string, number]> = [
    ["PDH", 305], ["PDL", -288], ["EQH", 162], ["EQL", -155],
    ["ATH", 618], ["ATL", -572], ["swing_high", 88],
    ["swing_high", 234], ["swing_low", -95], ["swing_low", -210],
  ];
  return levels.map(([type, offset]) => ({
    price: +(base + offset + between(rand, -15, 15)).toFixed(2),
    level_type: type,
    swept: rand() < 0.28,
  }));
}

export function generateMockSweeps(
  startDate = "2025-10-01",
  endDate = "2025-11-30",
  rand: RandFn = Math.random
): SweepEvent[] {
  const sweeps: SweepEvent[] = [];
  const start = new Date(startDate + "T09:00:00Z");
  const end = new Date(endDate + "T16:00:00Z");
  const range = Math.max(MS_PER_DAY, end.getTime() - start.getTime());
  const count = Math.max(3, Math.min(20, Math.floor(range / (3 * MS_PER_DAY))));
  const step = range / count;
  let d = new Date(start.getTime() + between(rand, 0, step * 0.5));

  for (let i = 0; i < count; i++) {
    if (d > end) break;
    const buyside = rand() > 0.5;
    sweeps.push({
      price: +(19800 + (buyside ? 200 : -200) + between(rand, -80, 80)).toFixed(2),
      sweep_type: buyside ? "buyside" : "sellside",
      timestamp: d.toISOString(),
      timeframe: ["1h", "15m", "4h"][Math.floor(rand() * 3)],
    });
    d = new Date(d.getTime() + step + between(rand, -step * 0.2, step * 0.2));
  }
  return sweeps;
}

// ── Main entry point ─────────────────────────────────────────────────────
// Creates one seeded RNG per generator category so they are independent
// but each category is fully deterministic for the same parameters.
export function generateMockBacktestResult(
  startDate: string,
  endDate: string,
  interval = "1h",
  config: BotConfig = DEFAULT_CONFIG
): BacktestResult {
  const seed = paramSeed(startDate, endDate, interval, config);
  const barSec = TF_BAR_SEC[interval] ?? 3600;

  // Each generator gets its own seeded stream derived from the main seed.
  // XOR with distinct constants so they never share state.
  const tradeRand  = createSeededRand(seed);
  const ohlcRand   = createSeededRand(seed ^ 0xa5a5a5a5);
  const fvgRand    = createSeededRand(seed ^ 0xf0f0f0f0);
  const liqRand    = createSeededRand(seed ^ 0x0f0f0f0f);
  const sweepRand  = createSeededRand(seed ^ 0x5a5a5a5a);

  const trades = generateMockTrades(startDate, endDate, config, tradeRand);
  const equity_curve = buildEquityCurve(trades, config.initial_capital, startDate);
  const metrics = computeMockMetrics(trades, config.initial_capital);

  return {
    backtest_id: `mock-${startDate}-${endDate}-${interval}`,
    metrics,
    trades,
    equity_curve,
    config,
    fvg_summary: MOCK_FVG_SUMMARY,
    period_name: `${startDate} → ${endDate}`,
    ohlc_data: generateMockOHLC(startDate, endDate, barSec, ohlcRand),
    ohlc_by_timeframe: generateMockOHLCByTimeframe(startDate, endDate, ohlcRand),
    fvg_zones: generateMockFVGZones(fvgRand),
    liquidity_levels: generateMockLiquidityLevels(liqRand),
    sweeps: generateMockSweeps(startDate, endDate, sweepRand),
  };
}

// Static fallback (initial page load, before any backtest is run)
export const MOCK_BACKTEST_RESULT: BacktestResult = generateMockBacktestResult(
  "2025-10-01",
  "2025-11-30",
  "1h",
  DEFAULT_CONFIG
);
