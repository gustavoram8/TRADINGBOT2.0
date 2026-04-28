"""
Módulo de visualización del backtest.

Genera un reporte gráfico técnico por cada operación y un dashboard global con:
  1. Curva de equidad (equity curve) construida desde el flujo de PnL neto.
  2. Drawdown bajo la curva de equidad.
  3. Gráfico de velas del activo con superposición de los puntos de ejecución
     (entradas long/short, SL hits, TP hits y cierres manuales).

No depende de mplfinance: dibuja velas con matplotlib puro para evitar
dependencias adicionales y permitir headless rendering en CI/servidores.

Uso típico desde el orquestador (main.py o backtest.py):

    from reporting.visualization import (
        build_trade_report,
        plot_backtest_dashboard,
        export_trade_reports,
    )

    plot_backtest_dashboard(
        df_ohlc=df_1h,
        trades_df=result["trades_df"],
        initial_capital=ACCOUNT_BALANCE,
        out_path="reports/backtest_dashboard.png",
    )
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")  # Headless — seguro en servidores y CI; llamar antes de pyplot

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle


# ---------------------------------------------------------------------------
# Helpers de timezone
# ---------------------------------------------------------------------------
def _strip_tz(ts) -> pd.Timestamp:
    """Convierte cualquier Timestamp a tz-naive sin desplazar el valor."""
    t = pd.Timestamp(ts)
    return t.tz_convert(None) if t.tzinfo is not None else t


def _strip_tz_series(s: pd.Series) -> pd.Series:
    """Elimina timezone de una Series de datetimes."""
    s = pd.to_datetime(s, errors="coerce")
    if getattr(s.dt, "tz", None) is not None:
        return s.dt.tz_convert(None)
    return s


def _strip_tz_index(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if idx.tz is not None:
        return idx.tz_convert(None)
    return idx


# ---------------------------------------------------------------------------
# Reporte técnico por operación
# ---------------------------------------------------------------------------
@dataclass
class TradeReport:
    """Estructura canónica de reporte técnico por operación."""
    trade_id: int
    direction: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    duration_min: float
    entry_price: float
    exit_price: float
    sl_price: float
    tp_price: float
    contracts: int
    pnl_gross: float
    pnl_net: float
    commission: float
    rr_planned: float
    rr_realized: float
    mae_points: float
    mfe_points: float
    exit_reason: str
    equity_after: float

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["entry_time"] = self.entry_time.isoformat() if pd.notna(self.entry_time) else None
        d["exit_time"]  = self.exit_time.isoformat()  if pd.notna(self.exit_time)  else None
        return d


def build_trade_report(
    trades_df: pd.DataFrame,
    df_ohlc: pd.DataFrame,
    initial_capital: float,
) -> List[TradeReport]:
    """
    Construye un TradeReport por operación.

    MAE (Max Adverse Excursion) y MFE (Max Favorable Excursion) se calculan
    en puntos a partir del rango High/Low del OHLC entre entry_time y exit_time.
    """
    if trades_df is None or trades_df.empty:
        return []

    df = trades_df.copy()
    for col in ("entry_time", "exit_time", "timestamp"):
        if col in df.columns:
            df[col] = _strip_tz_series(df[col])

    equity = initial_capital + df["pnl_net"].cumsum()

    # OHLC normalizado a tz-naive
    ohlc = df_ohlc.copy()
    ohlc.index = _strip_tz_index(ohlc.index)

    reports: List[TradeReport] = []
    for i, row in df.reset_index(drop=True).iterrows():
        raw_et = row.get("entry_time") if pd.notna(row.get("entry_time", pd.NaT)) else row.get("timestamp")
        raw_xt = row.get("exit_time")  if pd.notna(row.get("exit_time",  pd.NaT)) else row.get("timestamp")
        et = _strip_tz(raw_et)
        xt = _strip_tz(raw_xt)

        entry_price = float(row["entry_price"])
        exit_price  = float(row["exit_price"])
        sl_price    = float(row["sl_price"])
        tp_price    = float(row["tp_price"])
        direction   = str(row["direction"])

        # MAE / MFE en puntos dentro de la ventana del trade
        mae_pts = mfe_pts = 0.0
        try:
            window = ohlc.loc[et:xt]
            if not window.empty:
                if direction == "long":
                    mfe_pts = float(window["High"].max() - entry_price)
                    mae_pts = float(entry_price - window["Low"].min())
                else:
                    mfe_pts = float(entry_price - window["Low"].min())
                    mae_pts = float(window["High"].max() - entry_price)
        except Exception:
            pass

        sl_pts = abs(entry_price - sl_price)
        tp_pts = abs(tp_price - entry_price)
        rr_planned  = (tp_pts / sl_pts) if sl_pts > 0 else 0.0
        realized_pts = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
        rr_realized  = (realized_pts / sl_pts) if sl_pts > 0 else 0.0
        duration_min = (xt - et).total_seconds() / 60.0 if pd.notna(et) and pd.notna(xt) else 0.0

        reports.append(TradeReport(
            trade_id=int(i + 1),
            direction=direction,
            entry_time=et,
            exit_time=xt,
            duration_min=round(duration_min, 1),
            entry_price=entry_price,
            exit_price=exit_price,
            sl_price=sl_price,
            tp_price=tp_price,
            contracts=int(row.get("contracts", 0)),
            pnl_gross=float(row.get("pnl_gross", 0.0)),
            pnl_net=float(row["pnl_net"]),
            commission=float(row.get("commission", 0.0)),
            rr_planned=round(rr_planned, 2),
            rr_realized=round(rr_realized, 2),
            mae_points=round(mae_pts, 2),
            mfe_points=round(mfe_pts, 2),
            exit_reason=str(row.get("reason", "")),
            equity_after=float(equity.iloc[i]),
        ))
    return reports


def trade_reports_to_dataframe(reports: List[TradeReport]) -> pd.DataFrame:
    return pd.DataFrame([r.to_dict() for r in reports]) if reports else pd.DataFrame()


# ---------------------------------------------------------------------------
# Render de velas japonesas (sin mplfinance)
# ---------------------------------------------------------------------------
def _draw_candles(ax: plt.Axes, df: pd.DataFrame, width_frac: float = 0.7) -> None:
    """Dibuja candlesticks con primitivas matplotlib (vlines + Rectangle)."""
    if df.empty:
        return

    # Convertir fechas a float para posicionar los patches
    x = mdates.date2num(df.index.to_pydatetime())
    bar_width = (x[1] - x[0]) * width_frac if len(x) > 1 else 1.0 / 24.0

    up   = (df["Close"] >= df["Open"]).values
    down = ~up

    # Mechas (vectorizado con vlines)
    ax.vlines(x, df["Low"].values, df["High"].values,
              color="#444444", linewidth=0.6, zorder=1)

    # Cuerpos — verde alcistas, rojo bajistas
    for mask, color in ((up, "#26a69a"), (down, "#ef5350")):
        for k in np.where(mask)[0]:
            o, c = float(df["Open"].iloc[k]), float(df["Close"].iloc[k])
            bottom = min(o, c)
            height = max(abs(c - o), bar_width * 0.04)  # cuerpo mínimo visible
            ax.add_patch(Rectangle(
                (x[k] - bar_width / 2, bottom), bar_width, height,
                facecolor=color, edgecolor=color, linewidth=0.4, zorder=2,
            ))

    ax.xaxis_date()


# ---------------------------------------------------------------------------
# Dashboard principal: equity curve + drawdown + candlesticks con trades
# ---------------------------------------------------------------------------
def plot_backtest_dashboard(
    df_ohlc: pd.DataFrame,
    trades_df: Optional[pd.DataFrame],
    initial_capital: float,
    out_path: str = "reports/backtest_dashboard.png",
    title: str = "ICT Trading Bot — Backtest Dashboard",
    max_candles: int = 800,
) -> Optional[str]:
    """
    Genera un dashboard PNG de 3 paneles:
        [1]  Curva de equidad con área sombreada ganancia/pérdida
        [2]  Drawdown corriente
        [3]  Candlesticks del activo con entradas, salidas y líneas trade-a-trade

    Parameters
    ----------
    df_ohlc        : OHLCV con DatetimeIndex (cualquier TF).
    trades_df      : DataFrame de trades de ICTStrategy.get_trades_df().
    initial_capital: Capital inicial para construir equity.
    out_path       : Ruta del PNG (el directorio se crea si no existe).
    title          : Título del dashboard.
    max_candles    : Límite visual de velas (downsample estético, no afecta equity).

    Returns
    -------
    Ruta del PNG guardado, o None si df_ohlc está vacío.
    """
    if df_ohlc is None or df_ohlc.empty:
        print("[VIZ] OHLC vacío — no se generó dashboard.")
        return None

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # ── Construir curva de equity y drawdown ────────────────────────────────
    if trades_df is not None and not trades_df.empty:
        ts_col = "exit_time" if "exit_time" in trades_df.columns else "timestamp"
        eq_df = trades_df[[ts_col, "pnl_net"]].copy()
        eq_df[ts_col] = _strip_tz_series(eq_df[ts_col])
        eq_df = eq_df.sort_values(ts_col).reset_index(drop=True)
        eq_df["equity"] = initial_capital + eq_df["pnl_net"].cumsum()

        # Anclar inicio de la equity al inicio del periodo OHLC
        first_ts = _strip_tz(df_ohlc.index[0])
        first_eq_ts = pd.Timestamp(eq_df[ts_col].iloc[0])
        if first_eq_ts > first_ts:
            anchor = pd.DataFrame(
                {ts_col: [first_ts], "pnl_net": [0.0], "equity": [initial_capital]}
            )
            eq_df = pd.concat([anchor, eq_df], ignore_index=True)

        # Anclar fin de la equity al final del periodo OHLC
        last_ts = _strip_tz(df_ohlc.index[-1])
        last_eq_ts = pd.Timestamp(eq_df[ts_col].iloc[-1])
        if last_eq_ts < last_ts:
            tail = pd.DataFrame(
                {ts_col: [last_ts], "pnl_net": [0.0], "equity": [eq_df["equity"].iloc[-1]]}
            )
            eq_df = pd.concat([eq_df, tail], ignore_index=True)

        eq_df["running_max"] = eq_df["equity"].cummax()
        eq_df["drawdown"] = eq_df["equity"] - eq_df["running_max"]
    else:
        ts_col = "timestamp"
        eq_df = pd.DataFrame({
            ts_col: [_strip_tz(df_ohlc.index[0]), _strip_tz(df_ohlc.index[-1])],
            "equity":      [initial_capital, initial_capital],
            "running_max": [initial_capital, initial_capital],
            "drawdown":    [0.0, 0.0],
        })

    # ── Downsample visual del OHLC (no afecta cálculos) ────────────────────
    df_plot = df_ohlc.copy()
    df_plot.index = _strip_tz_index(df_plot.index)
    if len(df_plot) > max_candles:
        step = max(1, len(df_plot) // max_candles)
        df_plot = df_plot.iloc[::step]

    # ── Figura ──────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 12), constrained_layout=True)
    gs  = fig.add_gridspec(3, 1, height_ratios=[2.2, 1.0, 3.2])
    ax_eq = fig.add_subplot(gs[0])
    ax_dd = fig.add_subplot(gs[1], sharex=ax_eq)
    ax_px = fig.add_subplot(gs[2])
    fig.suptitle(title, fontsize=14, fontweight="bold", y=1.01)

    final_eq    = float(eq_df["equity"].iloc[-1])
    pct_return  = (final_eq - initial_capital) / initial_capital * 100
    max_dd_usd  = float(eq_df["drawdown"].min())

    # Panel 1 — Equity curve
    ax_eq.plot(eq_df[ts_col], eq_df["equity"],
               color="#1f77b4", linewidth=1.8, label="Equity", zorder=3)
    ax_eq.axhline(initial_capital, color="#888", linestyle="--",
                  linewidth=0.9, label=f"Inicial ${initial_capital:,.0f}", zorder=2)
    above = eq_df["equity"] >= initial_capital
    ax_eq.fill_between(eq_df[ts_col], initial_capital, eq_df["equity"],
                       where=above,  alpha=0.15, color="#26a69a", zorder=1)
    ax_eq.fill_between(eq_df[ts_col], initial_capital, eq_df["equity"],
                       where=~above, alpha=0.20, color="#ef5350", zorder=1)
    ax_eq.set_ylabel("Equity (USD)", fontsize=9)
    ax_eq.set_title(
        f"Curva de Equidad  |  Final: ${final_eq:,.0f}  ({pct_return:+.2f}%)",
        fontsize=10,
    )
    ax_eq.legend(loc="upper left", fontsize=8)
    ax_eq.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"${v:,.0f}")
    )
    ax_eq.grid(alpha=0.22)

    # Panel 2 — Drawdown
    ax_dd.fill_between(eq_df[ts_col], 0, eq_df["drawdown"],
                       color="#ef5350", alpha=0.60)
    ax_dd.axhline(0, color="#888", linewidth=0.6)
    ax_dd.set_ylabel("Drawdown (USD)", fontsize=9)
    ax_dd.set_title(f"Drawdown corriente  |  Máx: ${max_dd_usd:,.0f}", fontsize=10)
    ax_dd.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"${v:,.0f}")
    )
    ax_dd.grid(alpha=0.22)

    # Panel 3 — Candlesticks
    _draw_candles(ax_px, df_plot)
    ax_px.set_ylabel("Precio (puntos)", fontsize=9)
    ax_px.set_title("Precio + Ejecuciones", fontsize=10)
    ax_px.grid(alpha=0.18)

    if trades_df is not None and not trades_df.empty:
        td = trades_df.copy()
        for col in ("entry_time", "exit_time"):
            if col in td.columns:
                td[col] = _strip_tz_series(td[col])

        longs  = td[td["direction"] == "long"]
        shorts = td[td["direction"] == "short"]
        wins   = td[td["pnl_net"] > 0]
        losses = td[td["pnl_net"] <= 0]

        # Entradas
        if not longs.empty:
            ax_px.scatter(longs["entry_time"], longs["entry_price"],
                          marker="^", s=100, color="#1b5e20",
                          edgecolor="white", linewidth=0.8, zorder=5,
                          label=f"Long entry  ({len(longs)})")
        if not shorts.empty:
            ax_px.scatter(shorts["entry_time"], shorts["entry_price"],
                          marker="v", s=100, color="#b71c1c",
                          edgecolor="white", linewidth=0.8, zorder=5,
                          label=f"Short entry ({len(shorts)})")

        # Salidas — diferenciamos WIN (circle) y LOSS (×)
        if not wins.empty:
            ax_px.scatter(wins["exit_time"], wins["exit_price"],
                          marker="o", s=80, facecolor="#26a69a",
                          edgecolor="black", linewidth=0.7, zorder=6,
                          label=f"Exit WIN   ({len(wins)})")
        if not losses.empty:
            ax_px.scatter(losses["exit_time"], losses["exit_price"],
                          marker="X", s=90, facecolor="#c62828",
                          edgecolor="black", linewidth=0.7, zorder=6,
                          label=f"Exit LOSS  ({len(losses)})")

        # Línea entry → exit por cada trade
        for _, r in td.iterrows():
            color = "#26a69a" if r["pnl_net"] > 0 else "#ef5350"
            ax_px.plot(
                [r["entry_time"], r["exit_time"]],
                [r["entry_price"], r["exit_price"]],
                color=color, alpha=0.40, linewidth=0.9, zorder=3,
            )

        ax_px.legend(loc="upper left", fontsize=8, ncol=2)

    # Formato de eje X en los tres paneles
    locator   = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    for ax in (ax_eq, ax_dd, ax_px):
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        plt.setp(ax.get_xticklabels(), fontsize=7)

    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"[VIZ] Dashboard guardado → {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Exportar reporte por operación a CSV + JSON
# ---------------------------------------------------------------------------
def export_trade_reports(
    reports: List[TradeReport],
    out_dir: str = "reports",
    basename: Optional[str] = None,
) -> Dict[str, str]:
    """Persiste la lista de TradeReports en CSV y JSON. Retorna las rutas."""
    if not reports:
        return {}
    os.makedirs(out_dir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = basename or f"trade_reports_{ts}"
    csv_path  = os.path.join(out_dir, f"{base}.csv")
    json_path = os.path.join(out_dir, f"{base}.json")

    df = trade_reports_to_dataframe(reports)
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, date_format="iso")
    print(f"[VIZ] Trade reports → {csv_path}  |  {json_path}")
    return {"csv": csv_path, "json": json_path}
