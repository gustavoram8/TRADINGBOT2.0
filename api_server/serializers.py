"""
Pure transformation layer: takes the dict returned by ``backtest.run_backtest``
(which contains a PerformanceMetrics dataclass, a trades DataFrame, the
strategy instance, indicator state, etc.) and produces the JSON payload
expected by the Next.js frontend (``BacktestResult`` in lib/types.ts).

This module DOES NOT import or modify any strategy / indicator code.
It only reads the existing outputs and reshapes them.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# =============================================================================
# Datetime helpers
# =============================================================================
def _to_iso(value: Any) -> str:
    """Best-effort conversion of any datetime-like value to an ISO 8601 string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (pd.Timestamp, datetime)):
        # Strip tz so the JSON is consistent (frontend treats everything as UTC)
        if hasattr(value, "tz") and getattr(value, "tz", None) is not None:
            value = value.tz_convert("UTC").tz_localize(None)
        elif isinstance(value, datetime) and value.tzinfo is not None:
            value = value.replace(tzinfo=None)
        return pd.Timestamp(value).isoformat()
    try:
        return pd.Timestamp(value).isoformat()
    except Exception:
        return str(value)


def _to_unix_seconds(value: Any) -> int:
    """Convert any datetime to Unix epoch seconds (lightweight-charts format)."""
    if value is None:
        return 0
    ts = pd.Timestamp(value)
    if ts.tz is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return int(ts.timestamp())


def _safe_float(x: Any, default: float = 0.0) -> float:
    """Convert any numeric / None / inf to a finite float."""
    try:
        v = float(x)
        if not np.isfinite(v):
            return default
        return v
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


# =============================================================================
# Metrics
# =============================================================================
def serialize_metrics(metrics: Any) -> Dict[str, Any]:
    """
    Convert validation.metrics.PerformanceMetrics → frontend dict.

    NOTE on percent fields:
      - win_rate is already 0-1 from Python (e.g. 0.65 = 65%).
      - total_return_pct and max_drawdown_pct come from Python as ×100
        (e.g. 4.0 = 4%). We divide by 100 here so the frontend's fmtPct()
        (which also multiplies ×100) displays them correctly.
    """
    def _pct(v: Any) -> float:
        return _safe_float(v) / 100.0

    return {
        "total_trades": _safe_int(getattr(metrics, "total_trades", 0)),
        "winning_trades": _safe_int(getattr(metrics, "winning_trades", 0)),
        "losing_trades": _safe_int(getattr(metrics, "losing_trades", 0)),
        "win_rate": _safe_float(getattr(metrics, "win_rate", 0.0)),
        "profit_factor": _safe_float(getattr(metrics, "profit_factor", 0.0)),
        "total_pnl": _safe_float(getattr(metrics, "total_pnl", 0.0)),
        "total_pnl_gross": _safe_float(getattr(metrics, "total_pnl_gross", 0.0)),
        "total_commission": _safe_float(getattr(metrics, "total_commission", 0.0)),
        "initial_balance": _safe_float(getattr(metrics, "initial_balance", 0.0)),
        "final_balance": _safe_float(getattr(metrics, "final_balance", 0.0)),
        "total_return_pct": _pct(getattr(metrics, "total_return_pct", 0.0)),
        "avg_win": _safe_float(getattr(metrics, "avg_win", 0.0)),
        "avg_loss": _safe_float(getattr(metrics, "avg_loss", 0.0)),
        "expectancy": _safe_float(getattr(metrics, "expectancy", 0.0)),
        "largest_win": _safe_float(getattr(metrics, "largest_win", 0.0)),
        "largest_loss": _safe_float(getattr(metrics, "largest_loss", 0.0)),
        "max_drawdown_usd": _safe_float(getattr(metrics, "max_drawdown_usd", 0.0)),
        "max_drawdown_pct": _pct(getattr(metrics, "max_drawdown_pct", 0.0)),
        "max_drawdown_duration_days": _safe_int(
            getattr(metrics, "max_drawdown_duration_days", 0)
        ),
        "avg_drawdown_usd": _safe_float(getattr(metrics, "avg_drawdown_usd", 0.0)),
        "best_day_pnl": _safe_float(getattr(metrics, "best_day_pnl", 0.0)),
        "worst_day_pnl": _safe_float(getattr(metrics, "worst_day_pnl", 0.0)),
        "sharpe_ratio": _safe_float(getattr(metrics, "sharpe_ratio", 0.0)),
        "sortino_ratio": _safe_float(getattr(metrics, "sortino_ratio", 0.0)),
        "avg_rr_ratio": _safe_float(getattr(metrics, "avg_rr_ratio", 0.0)),
        "trades_per_day": _safe_float(getattr(metrics, "trades_per_day", 0.0)),
        "avg_trade_duration_hours": _safe_float(
            getattr(metrics, "avg_trade_duration_hours", 0.0)
        ),
        "consistency_check_passed": bool(
            getattr(metrics, "consistency_check_passed", False)
        ),
    }


# =============================================================================
# Trades (DataFrame → list)
# =============================================================================
def serialize_trades(trades_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert the trades DataFrame produced by ICTStrategy.get_trades_df()
    into the ``Trade[]`` shape expected by the frontend.

    The strategy's _trades_log already carries: timestamp, direction,
    entry/exit prices, sl/tp, pnl_gross/net, commission, contracts, reason,
    entry_time, exit_time. We only reshape — no business logic.
    """
    if trades_df is None or trades_df.empty:
        return []

    out: List[Dict[str, Any]] = []
    for i, row in trades_df.reset_index(drop=True).iterrows():
        out.append({
            "id": f"trade-{i}",
            "timestamp": _to_iso(row.get("timestamp") or row.get("entry_time")),
            "entry_time": _to_iso(row.get("entry_time")),
            "exit_time": _to_iso(row.get("exit_time")),
            "direction": str(row.get("direction", "long")),
            "entry_price": _safe_float(row.get("entry_price")),
            "exit_price": _safe_float(row.get("exit_price")),
            "sl_price": _safe_float(row.get("sl_price")),
            "tp_price": _safe_float(row.get("tp_price")),
            "pnl_gross": _safe_float(row.get("pnl_gross")),
            "pnl_net": _safe_float(row.get("pnl_net")),
            "commission": _safe_float(row.get("commission")),
            "contracts": _safe_int(row.get("contracts")),
            "reason": str(row.get("reason", "")),
            # context will be filled in a later phase from the strategy's
            # setup scorer data; keep it absent for now so the journal page
            # shows real trades but without synthesized narrative.
        })
    return out


# =============================================================================
# Equity curve
# =============================================================================
def build_equity_curve(
    trades_df: pd.DataFrame,
    initial_balance: float,
    start_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build the equity curve from the trade list. We rebuild it here (instead
    of asking the strategy) so the response matches the frontend's
    ``EquityPoint[]`` shape exactly.
    """
    points: List[Dict[str, Any]] = []
    first_dt = (
        _to_iso(start_date)
        if start_date
        else (
            _to_iso(trades_df.iloc[0]["entry_time"])
            if trades_df is not None and not trades_df.empty
            else _to_iso(datetime.utcnow())
        )
    )
    points.append({
        "datetime": first_dt,
        "equity": float(initial_balance),
        "pnl": 0.0,
        "drawdown": 0.0,
        "drawdown_pct": 0.0,
    })

    if trades_df is None or trades_df.empty:
        return points

    equity = float(initial_balance)
    peak = equity
    for _, row in trades_df.iterrows():
        equity += _safe_float(row.get("pnl_net"))
        peak = max(peak, equity)
        dd = peak - equity
        points.append({
            "datetime": _to_iso(row.get("exit_time")),
            "equity": equity,
            "pnl": _safe_float(row.get("pnl_net")),
            "drawdown": dd,
            "drawdown_pct": (dd / peak) if peak > 0 else 0.0,
        })
    return points


# =============================================================================
# OHLC
# =============================================================================
def serialize_ohlc(df: pd.DataFrame, max_bars: int = 5000) -> List[Dict[str, Any]]:
    """
    Convert an OHLC DataFrame to the lightweight-charts wire format.
    Uses unix seconds for `time` and trims to the most recent ``max_bars``.
    """
    if df is None or df.empty:
        return []

    df_use = df.tail(max_bars) if len(df) > max_bars else df
    out: List[Dict[str, Any]] = []
    for ts, row in df_use.iterrows():
        out.append({
            "time": _to_unix_seconds(ts),
            "open": _safe_float(row.get("Open")),
            "high": _safe_float(row.get("High")),
            "low": _safe_float(row.get("Low")),
            "close": _safe_float(row.get("Close")),
            "volume": _safe_float(row.get("Volume", 0.0)),
        })
    return out


# =============================================================================
# Indicator state (FVGs / liquidity / sweeps)
# =============================================================================
def serialize_fvg_zones(indicator_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map FVGs from extract_indicator_state() to the frontend's FVGZone shape."""
    out: List[Dict[str, Any]] = []
    for f in (indicator_state or {}).get("fvgs", []):
        out.append({
            "fvg_type": f.get("fvg_type", "bullish"),
            "timeframe": f.get("timeframe", "1h"),
            "high": _safe_float(f.get("top")),
            "low": _safe_float(f.get("bottom")),
            "timestamp": _to_iso(f.get("timestamp")),
            "filled": f.get("status") in ("broken",),
        })
    return out


def serialize_liquidity_levels(indicator_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map liquidity levels to the frontend's LiquidityLevel shape."""
    out: List[Dict[str, Any]] = []
    for lvl in (indicator_state or {}).get("liquidity", []):
        label = str(lvl.get("label", ""))
        # Best-effort: the frontend's LiquidityLevel.level_type expects strings
        # like "PDH", "PDL", "swing_high". We pass the label through; the UI
        # already deals with arbitrary strings.
        out.append({
            "price": _safe_float(lvl.get("price")),
            "level_type": label,
            "timestamp": _to_iso(lvl.get("formed_at")),
            "swept": lvl.get("status") in ("swept", "taken"),
        })
    return out


def serialize_sweeps(indicator_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map sweep events to the frontend's SweepEvent shape."""
    out: List[Dict[str, Any]] = []
    for sw in (indicator_state or {}).get("sweeps", []):
        direction = sw.get("direction", "")
        sweep_type = "buyside" if direction == "upside" else "sellside"
        out.append({
            "price": _safe_float(sw.get("wick_extreme")),
            "sweep_type": sweep_type,
            "timestamp": _to_iso(sw.get("timestamp")),
            # No timeframe attached at this layer; UI tolerates it being absent.
        })
    return out


# =============================================================================
# FVG summary (per-timeframe counts)
# =============================================================================
def build_fvg_summary(indicator_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build per-TF FVG counts from the raw FVG list. Mirrors the FVGSummary
    shape used by the cards on the backtest page.
    """
    fvgs = (indicator_state or {}).get("fvgs", [])
    by_tf: Dict[str, List[Dict[str, Any]]] = {}
    for f in fvgs:
        by_tf.setdefault(f.get("timeframe", "?"), []).append(f)

    summary: List[Dict[str, Any]] = []
    for tf in ("1h", "15m", "5m", "1m", "4h"):
        items = by_tf.get(tf, [])
        if not items:
            # Always include 1h/15m/5m/1m even when empty so the UI cards stay stable
            if tf in ("1h", "15m", "5m", "1m"):
                summary.append({
                    "timeframe": tf,
                    "total": 0, "bullish": 0, "bearish": 0,
                    "decision": 0, "avg_confluence": 0.0,
                })
            continue
        bullish = sum(1 for f in items if f.get("fvg_type") == "bullish")
        bearish = sum(1 for f in items if f.get("fvg_type") == "bearish")
        # "decision" — FVGs that ended up active or tested (not broken)
        decision = sum(1 for f in items if f.get("status") in ("active", "tested"))
        summary.append({
            "timeframe": tf,
            "total": len(items),
            "bullish": bullish,
            "bearish": bearish,
            "decision": decision,
            "avg_confluence": 0.0,  # not currently exposed by the strategy
        })
    return summary


# =============================================================================
# Top-level: assemble the full BacktestResult JSON
# =============================================================================
def assemble_backtest_result(
    *,
    backtest_id: str,
    period_name: str,
    request_config: Dict[str, Any],
    metrics: Any,
    trades_df: pd.DataFrame,
    df_ohlc: pd.DataFrame,
    indicator_state: Dict[str, Any],
    start_date: str,
    ohlc_by_timeframe: Optional[Dict[str, pd.DataFrame]] = None,
) -> Dict[str, Any]:
    """
    Final glue: takes everything ``run_backtest`` produced and emits the
    BacktestResult JSON as defined in lib/types.ts.
    """
    base_ohlc = serialize_ohlc(df_ohlc)
    ohlc_tf_out: Dict[str, List[Dict[str, Any]]] = {}
    if ohlc_by_timeframe:
        for tf, df in ohlc_by_timeframe.items():
            if df is not None and not df.empty:
                ohlc_tf_out[tf] = serialize_ohlc(df)

    return {
        "backtest_id": backtest_id,
        "metrics": serialize_metrics(metrics),
        "trades": serialize_trades(trades_df),
        "equity_curve": build_equity_curve(
            trades_df,
            initial_balance=_safe_float(getattr(metrics, "initial_balance", 50000.0)),
            start_date=start_date,
        ),
        "config": request_config,
        "fvg_summary": build_fvg_summary(indicator_state),
        "period_name": period_name,
        "ohlc_data": base_ohlc,
        "ohlc_by_timeframe": ohlc_tf_out or None,
        "fvg_zones": serialize_fvg_zones(indicator_state),
        "liquidity_levels": serialize_liquidity_levels(indicator_state),
        "sweeps": serialize_sweeps(indicator_state),
    }
