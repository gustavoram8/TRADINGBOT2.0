"""
Dashboard interactivo estilo TradingView (Plotly).

Genera un HTML autónomo que muestra:
  • Velas japonesas del activo
  • FVGs (Fair Value Gaps) como rectángulos coloreados por dirección
    y opacidad por timeframe (4H > 1H > 15m > 5m)
  • Niveles de liquidez como líneas horizontales (PDH/PDL, EQH/EQL,
    swings, ATH/ATL) con etiquetas
  • Marcadores de sweeps de liquidez
  • Entradas / salidas de cada trade con líneas SL/TP
  • Curva de equidad y drawdown como subplots sincronizados

El HTML resultante se puede abrir en cualquier navegador y permite
zoom, pan, hover, leyendas conmutables — flujo análogo a TradingView.

Uso:
    from reporting.tradingview_chart import (
        extract_indicator_state,
        plot_tradingview_dashboard,
    )

    state = extract_indicator_state(strategy)   # objeto bt.Strategy del backtest
    plot_tradingview_dashboard(
        df_ohlc=df_1h,
        trades_df=result["trades_df"],
        indicator_state=state,
        initial_capital=ACCOUNT_BALANCE,
        out_path="reports/tv_dashboard.html",
    )
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    _PLOTLY_OK = True
except ImportError:
    _PLOTLY_OK = False


# ---------------------------------------------------------------------------
# Paleta de colores
# ---------------------------------------------------------------------------
FVG_BULL_COLOR = "rgba(38,166,154,{a})"     # verde teal — bullish
FVG_BEAR_COLOR = "rgba(239,83,80,{a})"      # rojo coral — bearish

# Opacidad de relleno por timeframe (mayor = más importante)
TF_OPACITY = {
    "4h":  0.28,
    "1h":  0.18,
    "base": 0.18,
    "15m": 0.12,
    "5m":  0.08,
    "1m":  0.05,
}
TF_BORDER = {
    "4h":  ("#00695c", 2.0),
    "1h":  ("#00897b", 1.4),
    "base": ("#00897b", 1.4),
    "15m": ("#26a69a", 1.0),
    "5m":  ("#80cbc4", 0.7),
    "1m":  ("#b2dfdb", 0.5),
}

LIQ_COLOR_MAP = {
    "PDH":  "#1565c0", "PDL": "#1565c0",
    "EQH":  "#f57c00", "EQL": "#f57c00",
    "ATH":  "#7b1fa2", "ATL": "#7b1fa2",
}
LIQ_DEFAULT_COLOR = "#9e9e9e"

CANDLE_UP   = "#26a69a"
CANDLE_DOWN = "#ef5350"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _tz_naive(ts) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    return t.tz_convert(None) if t.tzinfo is not None else t


def _tz_naive_index(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if idx.tz is not None:
        return idx.tz_convert(None)
    return idx


def _tz_naive_series(s: pd.Series) -> pd.Series:
    s = pd.to_datetime(s, errors="coerce")
    if getattr(s.dt, "tz", None) is not None:
        return s.dt.tz_convert(None)
    return s


def _classify_liq_label(label: str) -> str:
    """Map raw label like 'PDH 18450' or 'Swing 18412.5' to a category key."""
    up = label.upper()
    for key in ("PDH", "PDL", "EQH", "EQL", "ATH", "ATL"):
        if key in up:
            return key
    if "SWING" in up:
        return "SWING"
    return "OTHER"


# ---------------------------------------------------------------------------
# Extracción del estado de indicadores desde la estrategia
# ---------------------------------------------------------------------------
def extract_indicator_state(strategy: Any) -> Dict[str, List[Dict]]:
    """
    Toma una instancia de ICTStrategy (post-backtest) y extrae los indicadores
    como diccionarios serializables. No modifica la estrategia.
    """
    state: Dict[str, List[Dict]] = {"fvgs": [], "liquidity": [], "sweeps": []}
    if strategy is None:
        return state

    # FVGs por timeframe
    trackers = [
        ("1h",  getattr(strategy, "fvg_tracker", None)),
        ("4h",  getattr(strategy, "fvg_tracker_4h", None)),
        ("15m", getattr(strategy, "fvg_tracker_15m", None)),
        ("5m",  getattr(strategy, "fvg_tracker_5m", None)),
    ]
    for tf_label, tracker in trackers:
        if tracker is None:
            continue
        for f in getattr(tracker, "all_fvgs", []):
            state["fvgs"].append({
                "timeframe": tf_label,
                "type":      f.fvg_type.value,    # "bullish"/"bearish"
                "top":       float(f.top),
                "bottom":    float(f.bottom),
                "timestamp": _tz_naive(f.timestamp),
                "status":    f.status.value,      # active/tested/broken/dubious
                "size":      float(f.size),
                "midpoint":  float(f.midpoint),
                "candle_idx": int(getattr(f, "candle_idx", 0)),
            })

    # Liquidity levels + sweeps
    liq_map = getattr(strategy, "liq_map", None)
    if liq_map is not None:
        for lvl in getattr(liq_map, "levels", []):
            state["liquidity"].append({
                "label":     str(lvl.label),
                "price":     float(lvl.price),
                "side":      lvl.side.value,     # "above"/"below"
                "weight":    int(lvl.weight),
                "formed_at": _tz_naive(lvl.formed_at),
                "status":    lvl.status.value,   # untouched/swept/taken/invalidated
            })
        for sw in getattr(liq_map, "sweep_history", []):
            state["sweeps"].append({
                "label":        str(sw.level.label),
                "timestamp":    _tz_naive(sw.timestamp),
                "wick_extreme": float(sw.wick_extreme),
                "close_after":  float(sw.close_after),
                "direction":    sw.direction,    # upside/downside
            })

    return state


# ---------------------------------------------------------------------------
# Helpers de render
# ---------------------------------------------------------------------------
def _add_fvg_shapes(
    fig: go.Figure,
    fvgs: List[Dict],
    df_ohlc: pd.DataFrame,
    row: int = 1,
    max_per_tf: int = 25,
) -> None:
    """Dibuja FVGs como rectángulos. Acepta los más significativos por TF."""
    if not fvgs:
        return

    end_ts = _tz_naive(df_ohlc.index[-1])

    # Agrupar por TF y quedarnos con los N más recientes y de mayor tamaño
    by_tf: Dict[str, List[Dict]] = {}
    for f in fvgs:
        by_tf.setdefault(f["timeframe"], []).append(f)

    for tf, items in by_tf.items():
        # Ordenar por status (activos primero) y luego por tamaño
        items.sort(
            key=lambda x: (
                0 if x["status"] in ("active", "tested", "dubious") else 1,
                -x["size"],
            )
        )
        items = items[:max_per_tf]

        opacity = TF_OPACITY.get(tf, 0.10)
        border_color, border_w = TF_BORDER.get(tf, ("#888", 0.8))

        for f in items:
            x0 = _tz_naive(f["timestamp"])
            # Si está roto, lo extendemos sólo hasta su muerte aproximada;
            # si no, hasta el final del backtest.
            x1 = end_ts
            color_template = FVG_BULL_COLOR if f["type"] == "bullish" else FVG_BEAR_COLOR
            fill = color_template.format(a=opacity)
            line_dash = "dot" if f["status"] == "broken" else "solid"

            fig.add_shape(
                type="rect",
                xref=f"x{row}", yref=f"y{row}",
                x0=x0, x1=x1, y0=f["bottom"], y1=f["top"],
                fillcolor=fill,
                line=dict(color=border_color, width=border_w, dash=line_dash),
                layer="below",
                row=row, col=1,
            )

    # Leyenda manual (traces invisibles para activar/ocultar por TF)
    for tf in sorted(by_tf.keys()):
        for direction, color in (("Bull", FVG_BULL_COLOR.format(a=0.55)),
                                 ("Bear", FVG_BEAR_COLOR.format(a=0.55))):
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(size=14, color=color, symbol="square"),
                name=f"FVG {tf} {direction}",
                legendgroup=f"fvg_{tf}",
                showlegend=True,
                hoverinfo="skip",
            ), row=row, col=1)


def _add_liquidity_lines(
    fig: go.Figure,
    levels: List[Dict],
    df_ohlc: pd.DataFrame,
    row: int = 1,
    max_levels: int = 60,
) -> None:
    """Dibuja niveles de liquidez como líneas horizontales con etiqueta."""
    if not levels:
        return

    # Filtrar duplicados por (price, label) y priorizar peso
    seen: set = set()
    deduped: List[Dict] = []
    for lvl in sorted(levels, key=lambda l: (-l["weight"], l["formed_at"])):
        key = (round(lvl["price"], 2), lvl["label"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(lvl)
    deduped = deduped[:max_levels]

    x_start = _tz_naive(df_ohlc.index[0])
    x_end   = _tz_naive(df_ohlc.index[-1])

    for lvl in deduped:
        category = _classify_liq_label(lvl["label"])
        color = LIQ_COLOR_MAP.get(category, LIQ_DEFAULT_COLOR)
        # Estado: untouched = sólida, swept = punteada, otro = dash
        if lvl["status"] == "untouched":
            dash = "solid"; width = 1.4
        elif lvl["status"] == "swept":
            dash = "dot";   width = 1.0
        else:
            dash = "dash";  width = 0.9

        fig.add_shape(
            type="line",
            xref=f"x{row}", yref=f"y{row}",
            x0=x_start, x1=x_end,
            y0=lvl["price"], y1=lvl["price"],
            line=dict(color=color, width=width, dash=dash),
            layer="below",
            row=row, col=1,
        )

        # Etiqueta del nivel sobre el extremo derecho
        fig.add_annotation(
            xref=f"x{row}", yref=f"y{row}",
            x=x_end, y=lvl["price"],
            text=f"  {lvl['label']} ({lvl['weight']})",
            showarrow=False,
            xanchor="left", yanchor="middle",
            font=dict(size=9, color=color),
            row=row, col=1,
        )


def _add_sweep_markers(
    fig: go.Figure,
    sweeps: List[Dict],
    row: int = 1,
) -> None:
    """Marca los sweeps de liquidez con un marcador en el wick extremo."""
    if not sweeps:
        return

    up = [s for s in sweeps if s["direction"] == "upside"]
    dn = [s for s in sweeps if s["direction"] == "downside"]

    if up:
        fig.add_trace(go.Scatter(
            x=[s["timestamp"] for s in up],
            y=[s["wick_extreme"] for s in up],
            mode="markers",
            marker=dict(symbol="triangle-down", size=11,
                        color="#0d47a1",
                        line=dict(color="white", width=1)),
            name=f"Sweep buyside ({len(up)})",
            legendgroup="sweeps",
            hovertext=[f"Swept {s['label']}" for s in up],
            hoverinfo="text+x+y",
        ), row=row, col=1)

    if dn:
        fig.add_trace(go.Scatter(
            x=[s["timestamp"] for s in dn],
            y=[s["wick_extreme"] for s in dn],
            mode="markers",
            marker=dict(symbol="triangle-up", size=11,
                        color="#b71c1c",
                        line=dict(color="white", width=1)),
            name=f"Sweep sellside ({len(dn)})",
            legendgroup="sweeps",
            hovertext=[f"Swept {s['label']}" for s in dn],
            hoverinfo="text+x+y",
        ), row=row, col=1)


def _add_trade_overlays(
    fig: go.Figure,
    trades_df: pd.DataFrame,
    row: int = 1,
) -> None:
    """Marcadores de entrada/salida + líneas SL/TP por trade."""
    if trades_df is None or trades_df.empty:
        return

    td = trades_df.copy()
    for c in ("entry_time", "exit_time"):
        if c in td.columns:
            td[c] = _tz_naive_series(td[c])

    longs  = td[td["direction"] == "long"]
    shorts = td[td["direction"] == "short"]
    wins   = td[td["pnl_net"] > 0]
    losses = td[td["pnl_net"] <= 0]

    # Hover text por trade
    def _ht(r):
        return (
            f"{r['direction'].upper()} | "
            f"Entry {r['entry_price']:.1f} → Exit {r['exit_price']:.1f}<br>"
            f"SL {r['sl_price']:.1f} | TP {r['tp_price']:.1f}<br>"
            f"PnL ${r['pnl_net']:+,.2f} | {r.get('reason', '')}"
        )

    if not longs.empty:
        fig.add_trace(go.Scatter(
            x=longs["entry_time"], y=longs["entry_price"],
            mode="markers",
            marker=dict(symbol="triangle-up", size=14, color="#1b5e20",
                        line=dict(color="white", width=1.2)),
            name=f"Long entry ({len(longs)})",
            text=[_ht(r) for _, r in longs.iterrows()],
            hoverinfo="text+x",
        ), row=row, col=1)

    if not shorts.empty:
        fig.add_trace(go.Scatter(
            x=shorts["entry_time"], y=shorts["entry_price"],
            mode="markers",
            marker=dict(symbol="triangle-down", size=14, color="#b71c1c",
                        line=dict(color="white", width=1.2)),
            name=f"Short entry ({len(shorts)})",
            text=[_ht(r) for _, r in shorts.iterrows()],
            hoverinfo="text+x",
        ), row=row, col=1)

    if not wins.empty:
        fig.add_trace(go.Scatter(
            x=wins["exit_time"], y=wins["exit_price"],
            mode="markers",
            marker=dict(symbol="circle", size=11, color="#26a69a",
                        line=dict(color="black", width=0.8)),
            name=f"Exit WIN ({len(wins)})",
            text=[_ht(r) for _, r in wins.iterrows()],
            hoverinfo="text+x",
        ), row=row, col=1)

    if not losses.empty:
        fig.add_trace(go.Scatter(
            x=losses["exit_time"], y=losses["exit_price"],
            mode="markers",
            marker=dict(symbol="x", size=12, color="#c62828",
                        line=dict(color="black", width=0.8)),
            name=f"Exit LOSS ({len(losses)})",
            text=[_ht(r) for _, r in losses.iterrows()],
            hoverinfo="text+x",
        ), row=row, col=1)

    # Líneas entry → exit y niveles SL/TP por trade
    for _, r in td.iterrows():
        outcome = "#26a69a" if r["pnl_net"] > 0 else "#ef5350"
        # entry → exit
        fig.add_shape(
            type="line", xref=f"x{row}", yref=f"y{row}",
            x0=r["entry_time"], x1=r["exit_time"],
            y0=r["entry_price"], y1=r["exit_price"],
            line=dict(color=outcome, width=1.2, dash="dot"),
            layer="above", row=row, col=1,
        )
        # SL horizontal (durante el trade)
        fig.add_shape(
            type="line", xref=f"x{row}", yref=f"y{row}",
            x0=r["entry_time"], x1=r["exit_time"],
            y0=r["sl_price"], y1=r["sl_price"],
            line=dict(color="#c62828", width=0.8, dash="dash"),
            layer="above", row=row, col=1,
        )
        # TP horizontal
        fig.add_shape(
            type="line", xref=f"x{row}", yref=f"y{row}",
            x0=r["entry_time"], x1=r["exit_time"],
            y0=r["tp_price"], y1=r["tp_price"],
            line=dict(color="#1b5e20", width=0.8, dash="dash"),
            layer="above", row=row, col=1,
        )


# ---------------------------------------------------------------------------
# Dashboard principal
# ---------------------------------------------------------------------------
def plot_tradingview_dashboard(
    df_ohlc: pd.DataFrame,
    trades_df: Optional[pd.DataFrame],
    indicator_state: Optional[Dict[str, Any]],
    initial_capital: float,
    out_path: str = "reports/tv_dashboard.html",
    title: str = "ICT Trading Bot — Backtest",
    max_fvgs_per_tf: int = 25,
    max_liq_levels: int = 60,
    data_source_label: str = "yfinance | NQ=F",
) -> Optional[str]:
    """
    Genera un HTML interactivo (estilo TradingView) con velas, FVGs,
    liquidez, sweeps, trades, equity y drawdown.

    Returns
    -------
    Ruta del HTML, o None si Plotly no está instalado o df_ohlc vacío.
    """
    if not _PLOTLY_OK:
        print("[TV] Plotly no instalado — pip install plotly>=5.18")
        return None
    if df_ohlc is None or df_ohlc.empty:
        print("[TV] OHLC vacío — no se generó dashboard.")
        return None

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # ── Normalizar OHLC y construir equity ──────────────────────────────────
    df = df_ohlc.copy()
    df.index = _tz_naive_index(df.index)

    # Equity / drawdown
    if trades_df is not None and not trades_df.empty:
        ts_col = "exit_time" if "exit_time" in trades_df.columns else "timestamp"
        eq = trades_df[[ts_col, "pnl_net"]].copy()
        eq[ts_col] = _tz_naive_series(eq[ts_col])
        eq = eq.sort_values(ts_col).reset_index(drop=True)
        eq["equity"] = initial_capital + eq["pnl_net"].cumsum()

        first_ts = df.index[0]
        if eq[ts_col].iloc[0] > first_ts:
            eq = pd.concat([
                pd.DataFrame({ts_col: [first_ts], "pnl_net": [0.0],
                              "equity": [initial_capital]}),
                eq,
            ], ignore_index=True)
        last_ts = df.index[-1]
        if eq[ts_col].iloc[-1] < last_ts:
            eq = pd.concat([
                eq,
                pd.DataFrame({ts_col: [last_ts], "pnl_net": [0.0],
                              "equity": [eq["equity"].iloc[-1]]}),
            ], ignore_index=True)

        eq["running_max"] = eq["equity"].cummax()
        eq["drawdown"]    = eq["equity"] - eq["running_max"]
    else:
        ts_col = "timestamp"
        eq = pd.DataFrame({
            ts_col: [df.index[0], df.index[-1]],
            "pnl_net":     [0.0, 0.0],
            "equity":      [initial_capital, initial_capital],
            "running_max": [initial_capital, initial_capital],
            "drawdown":    [0.0, 0.0],
        })

    # ── Layout: 3 paneles compartiendo eje X ────────────────────────────────
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.62, 0.18, 0.20],
        subplot_titles=(
            "Precio + FVGs + Liquidez + Trades",
            "Curva de Equidad",
            "Drawdown",
        ),
    )

    # 1) Velas
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        increasing_line_color=CANDLE_UP, decreasing_line_color=CANDLE_DOWN,
        name="OHLC",
        showlegend=False,
        whiskerwidth=0.6,
    ), row=1, col=1)

    # 2) FVGs / liquidez / sweeps / trades
    state = indicator_state or {}
    _add_fvg_shapes(fig, state.get("fvgs", []), df, row=1,
                    max_per_tf=max_fvgs_per_tf)
    _add_liquidity_lines(fig, state.get("liquidity", []), df, row=1,
                         max_levels=max_liq_levels)
    _add_sweep_markers(fig, state.get("sweeps", []), row=1)
    _add_trade_overlays(fig, trades_df, row=1)

    # 3) Equity curve
    final_eq    = float(eq["equity"].iloc[-1])
    pct_return  = (final_eq - initial_capital) / initial_capital * 100
    max_dd_usd  = float(eq["drawdown"].min())

    fig.add_trace(go.Scatter(
        x=eq[ts_col], y=eq["equity"],
        mode="lines",
        line=dict(color="#1976d2", width=2),
        name="Equity",
        fill="tonexty",
        fillcolor="rgba(25,118,210,0.08)",
    ), row=2, col=1)
    fig.add_hline(
        y=initial_capital, row=2, col=1,
        line=dict(color="#888", width=0.8, dash="dash"),
        annotation_text=f"Capital inicial ${initial_capital:,.0f}",
        annotation_position="bottom right",
    )

    # 4) Drawdown
    fig.add_trace(go.Scatter(
        x=eq[ts_col], y=eq["drawdown"],
        mode="lines",
        line=dict(color="#c62828", width=1.4),
        fill="tozeroy",
        fillcolor="rgba(239,83,80,0.25)",
        name="Drawdown",
    ), row=3, col=1)

    # ── Layout final ────────────────────────────────────────────────────────
    n_fvgs   = len(state.get("fvgs", []))
    n_liq    = len(state.get("liquidity", []))
    n_swp    = len(state.get("sweeps", []))
    n_trades = 0 if trades_df is None or trades_df.empty else len(trades_df)

    subtitle = (
        f"<sub>Fuente de datos: <b>{data_source_label}</b>  |  "
        f"Final: ${final_eq:,.0f} ({pct_return:+.2f}%)  |  "
        f"DD máx: ${max_dd_usd:,.0f}  |  "
        f"Trades: {n_trades}  |  FVGs: {n_fvgs}  |  "
        f"Liq lvls: {n_liq}  |  Sweeps: {n_swp}</sub>"
    )

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b><br>{subtitle}",
            x=0.01, xanchor="left",
            font=dict(size=15),
        ),
        height=1100,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="v",
            x=1.01, y=1.0,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#ccc", borderwidth=1,
            font=dict(size=10),
        ),
        margin=dict(l=60, r=140, t=110, b=50),
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False,
        xaxis3_rangeslider_visible=False,
    )

    fig.update_yaxes(title_text="Precio (pts)", row=1, col=1)
    fig.update_yaxes(title_text="USD",          row=2, col=1)
    fig.update_yaxes(title_text="USD",          row=3, col=1)

    # Guardar HTML autónomo (incluye plotly.js)
    fig.write_html(
        out_path,
        include_plotlyjs="cdn",   # CDN: 200KB en lugar de embed 3MB
        full_html=True,
    )
    print(f"[TV] Dashboard interactivo → {out_path}")
    return out_path
