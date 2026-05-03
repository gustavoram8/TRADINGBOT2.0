"""
Pydantic models that mirror the TypeScript types in lib/types.ts.

These describe the *wire format* between the FastAPI server and the
Next.js frontend. They do NOT touch any strategy or indicator code.
"""
from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, Field


# =============================================================================
# REQUEST — what the frontend sends to POST /backtest
# =============================================================================
class BotConfigPayload(BaseModel):
    """
    Mirrors `BotConfig` in lib/types.ts. Sent by the frontend so the user
    can override the strategy's risk / FVG / structure parameters per run.

    Only fields that map to ICTStrategy params are forwarded. Extra fields
    (e.g. fvg_lookback_*) are accepted to keep the wire compatible with the
    frontend, even if the current strategy implementation doesn't read them.
    """
    name: str = "Custom"
    initial_capital: float
    max_daily_loss: float
    max_trades_per_day: int
    default_contracts: int

    max_loss_per_trade: float = 600.0
    big_loss_threshold: float
    big_win_threshold: float

    # FVG lookback / max — accepted but not all consumed by the strategy
    fvg_lookback_1h: int
    fvg_lookback_15m: int
    fvg_lookback_5m: int
    fvg_lookback_1m: int
    fvg_max_1h: int
    fvg_max_15m: int
    fvg_max_5m: int
    fvg_max_1m: int

    fvg_search_range: float
    structure_lookback: int
    break_even_pct: float
    close_at_pct: float


class BacktestRequest(BaseModel):
    """Body of POST /backtest."""
    start_date: str = Field(..., description="ISO date YYYY-MM-DD")
    end_date: str = Field(..., description="ISO date YYYY-MM-DD")
    interval: str = Field("1h", description="Base TF: 1m | 5m | 15m | 1h")
    config: BotConfigPayload


# =============================================================================
# RESPONSE — what /backtest returns
# Each model below mirrors its counterpart in lib/types.ts exactly.
# =============================================================================
class TradeSetupCondition(BaseModel):
    label: str
    detail: str
    score: float
    passed: bool


class TradeContextOut(BaseModel):
    market_structure: Literal["bullish", "bearish", "ranging"]
    price_zone: Literal["discount", "premium", "equilibrium"]
    killzone: str
    trigger_fvg_timeframe: str
    trigger_fvg_type: Literal["bullish", "bearish"]
    trigger_fvg_size_points: float
    fvg_confluence: List[Dict]
    nearest_target: str
    recent_sweep: Optional[str] = None
    setup_score: float
    min_score: float
    conditions: List[TradeSetupCondition]
    exit_detail: str


class TradeOut(BaseModel):
    id: Optional[str] = None
    timestamp: str
    entry_time: str
    exit_time: str
    direction: Literal["long", "short"]
    entry_price: float
    exit_price: float
    sl_price: float
    tp_price: float
    pnl_gross: float
    pnl_net: float
    commission: float
    contracts: int
    reason: str
    context: Optional[TradeContextOut] = None


class EquityPointOut(BaseModel):
    datetime: str
    equity: float
    pnl: float
    drawdown: float
    drawdown_pct: float


class PerformanceMetricsOut(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    total_pnl: float
    total_pnl_gross: float
    total_commission: float
    initial_balance: float
    final_balance: float
    total_return_pct: float
    avg_win: float
    avg_loss: float
    expectancy: float
    largest_win: float
    largest_loss: float
    max_drawdown_usd: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    avg_drawdown_usd: float
    best_day_pnl: float
    worst_day_pnl: float
    sharpe_ratio: float
    sortino_ratio: float
    avg_rr_ratio: float
    trades_per_day: float
    avg_trade_duration_hours: float
    consistency_check_passed: bool


class FVGSummaryOut(BaseModel):
    timeframe: str
    total: int
    bullish: int
    bearish: int
    decision: int
    avg_confluence: float


class OHLCBarOut(BaseModel):
    time: int  # unix seconds — TradingView lightweight-charts format
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


class FVGZoneOut(BaseModel):
    fvg_type: Literal["bullish", "bearish"]
    timeframe: str
    high: float
    low: float
    timestamp: Optional[str] = None
    filled: Optional[bool] = None


class LiquidityLevelOut(BaseModel):
    price: float
    level_type: str
    timestamp: Optional[str] = None
    swept: Optional[bool] = None


class SweepEventOut(BaseModel):
    price: float
    sweep_type: Literal["buyside", "sellside"]
    timestamp: str
    timeframe: Optional[str] = None


class BacktestResultOut(BaseModel):
    backtest_id: Optional[str] = None
    metrics: PerformanceMetricsOut
    trades: List[TradeOut]
    equity_curve: List[EquityPointOut]
    config: BotConfigPayload
    fvg_summary: List[FVGSummaryOut]
    period_name: Optional[str] = None
    ohlc_data: Optional[List[OHLCBarOut]] = None
    ohlc_by_timeframe: Optional[Dict[str, List[OHLCBarOut]]] = None
    fvg_zones: Optional[List[FVGZoneOut]] = None
    liquidity_levels: Optional[List[LiquidityLevelOut]] = None
    sweeps: Optional[List[SweepEventOut]] = None
