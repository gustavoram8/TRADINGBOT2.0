export interface Trade {
  id?: string;
  timestamp: string;
  entry_time: string;
  exit_time: string;
  direction: "long" | "short";
  entry_price: number;
  exit_price: number;
  sl_price: number;
  tp_price: number;
  pnl_gross: number;
  pnl_net: number;
  commission: number;
  contracts: number;
  reason: string;
}

export interface EquityPoint {
  datetime: string;
  equity: number;
  pnl: number;
  drawdown: number;
  drawdown_pct: number;
}

export interface FVGSummary {
  timeframe: string;
  total: number;
  bullish: number;
  bearish: number;
  decision: number;
  avg_confluence: number;
}

export interface PerformanceMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  total_pnl: number;
  total_pnl_gross: number;
  total_commission: number;
  initial_balance: number;
  final_balance: number;
  total_return_pct: number;
  avg_win: number;
  avg_loss: number;
  expectancy: number;
  largest_win: number;
  largest_loss: number;
  max_drawdown_usd: number;
  max_drawdown_pct: number;
  max_drawdown_duration_days: number;
  avg_drawdown_usd: number;
  best_day_pnl: number;
  worst_day_pnl: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  avg_rr_ratio: number;
  trades_per_day: number;
  avg_trade_duration_hours: number;
  consistency_check_passed: boolean;
}

export interface BotConfig {
  name: string;
  initial_capital: number;
  max_daily_loss: number;
  max_trades_per_day: number;
  default_contracts: number;
  big_loss_threshold: number;
  big_win_threshold: number;
  fvg_lookback_1h: number;
  fvg_lookback_15m: number;
  fvg_lookback_5m: number;
  fvg_lookback_1m: number;
  fvg_max_1h: number;
  fvg_max_15m: number;
  fvg_max_5m: number;
  fvg_max_1m: number;
  fvg_search_range: number;
  structure_lookback: number;
  break_even_pct: number;
  close_at_pct: number;
}

export interface FVGZone {
  fvg_type: "bullish" | "bearish";
  timeframe: string;
  high: number;
  low: number;
  timestamp?: string;
  filled?: boolean;
}

export interface LiquidityLevel {
  price: number;
  level_type: string;
  timestamp?: string;
  swept?: boolean;
}

export interface SweepEvent {
  price: number;
  sweep_type: "buyside" | "sellside";
  timestamp: string;
  timeframe?: string;
}

export interface BacktestResult {
  backtest_id?: string;
  metrics: PerformanceMetrics;
  trades: Trade[];
  equity_curve: EquityPoint[];
  config: BotConfig;
  fvg_summary: FVGSummary[];
  period_name?: string;
  ohlc_data?: OHLCBar[];
  ohlc_by_timeframe?: Record<string, OHLCBar[]>;
  fvg_zones?: FVGZone[];
  liquidity_levels?: LiquidityLevel[];
  sweeps?: SweepEvent[];
}

export interface MonteCarloResult {
  prob_profit: number;
  max_dd_p95: number;
  final_pnl_p50: number;
  prob_exceed_dd: number;
  is_viable: boolean;
  iterations: number;
}

export interface ConsistencyResult {
  passed: boolean;
  ratio: number;
  threshold: number;
  top_days_pnl: number;
  total_positive_pnl: number;
}

export interface DailyPnl {
  date: string;
  pnl: number;
  trade_count: number;
  win_count: number;
}

export interface HourlyPerformance {
  hour: number;
  total_pnl: number;
  count: number;
  win_rate: number;
}

export interface OHLCBar {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export type GoNoGoStatus = "GO" | "CAUTION" | "NO-GO";

export interface GoNoGoCheck {
  label: string;
  passed: boolean;
  value: string;
  threshold: string;
}
