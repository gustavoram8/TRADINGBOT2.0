"""
Módulo de visualización del backtest.

Genera un reporte gráfico técnico por cada operación y un dashboard global con:
  1. Curva de equidad (equity curve) construida desde el flujo de PnL neto.
  2. Drawdown bajo la curva de equidad.
  3. Gráfico de velas del activo con superposición de los puntos de ejecución
     (entradas long/short, SL hits, TP hits y cierres manuales).

No depende de mplfinance: dibuja velas con matplotlib puro para evitar
dependencias adicionales y permitir headless rendering en CI.

Uso típico desde el orquestador:
    from reporting.visualization import (
        build_trade_report,
        plot_backtest_dashboard,
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

matplotlib.use("Agg")  # Backend headless — seguro en servidores y CI

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle


# ---------------------------------------------------------------------------
# Reporte técnico por operación
# ---------------------------------------------------------------------------
@dataclass
class TradeReport:
    """Estructura canónica de reporte por operación."""
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
    Construye un TradeReport por operación. MAE/MFE se calculan a partir del
    rango High/Low entre entry_time y exit_time del df_ohlc.
    """
    if trades_df is None or trades_df.empty:
        return []

    # Asegurar tipos de timestamp
    df = trades_df.copy()
    for col in ("entry_time", "exit_time", "timestamp"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Equity acumulada
    equity = initial_capital + df["pnl_net"].cumsum()

    # Normalizar índice del OHLC a tz-naive para comparar de forma robusta
    ohlc = df_ohlc.copy()
    if isinstance(ohlc.index, pd.DatetimeIndex) and ohlc.index.tz is not None:
        ohlc.index = ohlc.index.tz_localize(None)

    reports: List[TradeReport] = []
    for i, row in df.reset_index(drop=True).iterrows():
        et = row.get("entry_time") or row.get("timestamp")
        xt = row.get("exit_time")  or row.get("timestamp")
        et = pd.Timestamp(et).tz_localize(None) if pd.notna(et) and getattr(et, "tzinfo", None) else pd.Timestamp(et)
        xt = pd.Timestamp(xt).tz_localize(None) if pd.notna(xt) and getattr(xt, "tzinfo", None) else pd.Timestamp(xt)

        entry_price = float(row["entry_price"])
        exit_price  = float(row["exit_price"])
        sl_price    = float(row["sl_price"])
        tp_price    = float(row["tp_price"])
        direction   = str(row["direction"])

        # MAE / MFE en puntos
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
# Render de velas (sin mplfinance)
# ---------------------------------------------------------------------------
def _draw_candles(ax: plt.Axes, df: pd.DataFrame, width_frac: float = 0.7) -> None:
    """Dibuja un gráfico OHLC tipo velas japonesas usando primitivas de matplotlib."""
    if df.empty:
        return

    # Numérico para X (más rápido que datetimes en patches)
    x = mdates.date2num(df.index.to_pydatetime())
    if len(x) > 1:
        bar_width = (x[1] - x[0]) * width_frac
    else:
        bar_width = 1.0 / 24.0  # fallback ~1h

    up   = df["Close"] >= df["Open"]
    down = ~up

    # Mechas: usamos vlines (vectorizado)
    ax.vlines(x, df["Low"].values, df["High"].values, color="#444", linewidth=0.6, zorder=1)

    # Cuerpos
    for is_up, color in ((up, "#26a69a"), (down, "#ef5350")):
        idx = np.where(is_up.values)[0]
        for k in idx:
            o, c = df["Open"].iloc[k], df["Close"].iloc[k]
            bottom = min(o, c)
            height = max(abs(c - o), bar_width * 0.05)  # cuerpo mínimo visible
            ax.add_patch(Rectangle(
                (x[k] - bar_width / 2, bottom),
                bar_width, height,
                facecolor=color, edgecolor=color, linewidth=0.5, zorder=2,
            ))

    ax.xaxis_date()


# ---------------------------------------------------------------------------
# Dashboard principal: equity + drawdown + velas con ejecuciones
# ---------------------------------------------------------------------------
def plot_backtest_dashboard(
    df_ohlc: pd.DataFrame,
    trades_df: pd.DataFrame,
    initial_capital: float,
    out_path: str = "reports/backtest_dashboard.png",
    title: str = "ICT Trading Bot — Backtest Dashboard",
    max_candles: int = 800,
) -> Optional[str]:
    """
    Genera un dashboard de 3 paneles:
        [1] Curva de equidad
        [2] Drawdown
        [3] Candlesticks del activo con marcadores de ejecución superpuestos

    Parameters
    ----------
    df_ohlc : DataFrame con DatetimeIndex y columnas Open/High/Low/Close.
    trades_df : DataFrame de operaciones (esquema producido por
        ICTStrategy.get_trades_df()).
    initial_capital : Capital inicial para construir la equity.
    out_path : Ruta del PNG resultante (se crea el directorio si falta).
    title : Título superior del dashboard.
    max_candles : Si el OHLC excede este límite, se hace downsampling visual
        para mantener el render legible. NO afecta los cálculos de equity.

    Returns
    -------
    Ruta del archivo guardado, o None si no se pudo generar.
    """
    if df_ohlc is None or df_ohlc.empty:
        print("[VIZ] OHLC vacío — no se generó dashboard.")
        return None

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # --- Equity & drawdown -------------------------------------------------
    if trades_df is not None and not trades_df.empty:
        ts_col = "exit_time" if "exit_time" in trades_df.columns else "timestamp"
        eq_df = trades_df[[ts_col, "pnl_net"]].copy()
        eq_df[ts_col] = pd.to_datetime(eq_df[ts_col])
        eq_df = eq_df.sort_values(ts_col).reset_index(drop=True)
        eq_df["equity"] = initial_capital + eq_df["pnl_net"].cumsum()

        # Anclar al inicio del periodo
        first_ts = df_ohlc.index[0]
        if eq_df[ts_col].iloc[0] > first_ts:
            eq_df = pd.concat([
                pd.DataFrame({ts_col: [first_ts], "pnl_net": [0.0],
                              "equity": [initial_capital]}),
                eq_df,
            ], ignore_index=True)

        running_max = eq_df["equity"].cummax()
        eq_df["drawdown"] = eq_df["equity"] - running_max
    else:
        eq_df = pd.DataFrame({
            "timestamp": [df_ohlc.index[0], df_ohlc.index[-1]],
            "equity":    [initial_capital, initial_capital],
            "drawdown":  [0.0, 0.0],
        })
        ts_col = "timestamp"

    # --- Downsample del OHLC sólo para el render ---------------------------
    df_plot = df_ohlc
    if len(df_ohlc) > max_candles:
        step = max(1, len(df_ohlc) // max_candles)
        df_plot = df_ohlc.iloc[::step].copy()

    if isinstance(df_plot.index, pd.DatetimeIndex) and df_plot.index.tz is not None:
        df_plot = df_plot.copy()
        df_plot.index = df_plot.index.tz_localize(None)

    # --- Figura ------------------------------------------------------------
    fig = plt.figure(figsize=(15, 11), constrained_layout=True)
    gs = fig.add_gridspec(3, 1, height_ratios=[2.0, 1.0, 3.0])
    ax_eq   = fig.add_subplot(gs[0])
    ax_dd   = fig.add_subplot(gs[1], sharex=ax_eq)
    ax_px   = fig.add_subplot(gs[2])

    fig.suptitle(title, fontsize=14, fontweight="bold")

    # 1) Equity curve
    ax_eq.plot(eq_df[ts_col], eq_df["equity"], color="#1f77b4", linewidth=1.6,
               label="Equity")
    ax_eq.axhline(initial_capital, color="#888", linestyle="--", linewidth=0.8,
                  label=f"Inicial ${initial_capital:,.0f}")
    final_eq = eq_df["equity"].iloc[-1]
    ax_eq.fill_between(eq_df[ts_col], initial_capital, eq_df["equity"],
                       where=(eq_df["equity"] >= initial_capital),
                       alpha=0.15, color="#26a69a")
    ax_eq.fill_between(eq_df[ts_col], initial_capital, eq_df["equity"],
                       where=(eq_df["equity"] <  initial_capital),
                       alpha=0.15, color="#ef5350")
    ax_eq.set_ylabel("Equity (USD)")
    ax_eq.set_title(
        f"Curva de equidad — Final ${final_eq:,.0f} "
        f"({(final_eq - initial_capital) / initial_capital * 100:+.2f}%)"
    )
    ax_eq.legend(loc="upper left", fontsize=9)
    ax_eq.grid(alpha=0.25)

    # 2) Drawdown
    ax_dd.fill_between(eq_df[ts_col], 0, eq_df["drawdown"],
                       color="#ef5350", alpha=0.55)
    ax_dd.set_ylabel("Drawdown (USD)")
    ax_dd.set_title(f"Drawdown — Máx ${eq_df['drawdown'].min():,.0f}")
    ax_dd.grid(alpha=0.25)

    # 3) Candlesticks + ejecuciones
    _draw_candles(ax_px, df_plot)
    ax_px.set_title("Precio + Ejecuciones")
    ax_px.set_ylabel(f"Precio")
    ax_px.grid(alpha=0.2)

    if trades_df is not None and not trades_df.empty:
        td = trades_df.copy()
        for col in ("entry_time", "exit_time"):
            if col in td.columns:
                td[col] = pd.to_datetime(td[col])
                if td[col].dt.tz is not None:
                    td[col] = td[col].dt.tz_localize(None)

        longs  = td[td["direction"] == "long"]
        shorts = td[td["direction"] == "short"]
        wins   = td[td["pnl_net"] > 0]
        losses = td[td["pnl_net"] <= 0]

        # Entradas
        if not longs.empty:
            ax_px.scatter(longs["entry_time"], longs["entry_price"],
                          marker="^", s=90, color="#1b5e20",
                          edgecolor="white", linewidth=0.8, zorder=5,
                          label=f"Long entry ({len(longs)})")
        if not shorts.empty:
            ax_px.scatter(shorts["entry_time"], shorts["entry_price"],
                          marker="v", s=90, color="#b71c1c",
                          edgecolor="white", linewidth=0.8, zorder=5,
                          label=f"Short entry ({len(shorts)})")

        # Salidas
        if not wins.empty:
            ax_px.scatter(wins["exit_time"], wins["exit_price"],
                          marker="o", s=70, facecolor="#26a69a",
                          edgecolor="black", linewidth=0.6, zorder=6,
                          label=f"Exit WIN ({len(wins)})")
        if not losses.empty:
            ax_px.scatter(losses["exit_time"], losses["exit_price"],
                          marker="x", s=80, color="#c62828", linewidth=2.0,
                          zorder=6, label=f"Exit LOSS ({len(losses)})")

        # Línea entry→exit por trade (gris translúcido)
        for _, r in td.iterrows():
            ax_px.plot([r["entry_time"], r["exit_time"]],
                       [r["entry_price"], r["exit_price"]],
                       color="#555", alpha=0.35, linewidth=0.7, zorder=3)

        ax_px.legend(loc="upper left", fontsize=8, ncol=2)

    # Formato de fechas
    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    for ax in (ax_eq, ax_dd, ax_px):
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"[VIZ] Dashboard guardado en {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Reporte técnico por operación → CSV/JSON
# ---------------------------------------------------------------------------
def export_trade_reports(
    reports: List[TradeReport],
    out_dir: str = "reports",
    basename: Optional[str] = None,
) -> Dict[str, str]:
    """Persiste el reporte por operación en CSV y JSON. Retorna las rutas."""
    if not reports:
        return {}
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = basename or f"trade_reports_{ts}"
    csv_path  = os.path.join(out_dir, f"{base}.csv")
    json_path = os.path.join(out_dir, f"{base}.json")

    df = trade_reports_to_dataframe(reports)
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, date_format="iso")
    print(f"[VIZ] Trade reports → {csv_path} | {json_path}")
    return {"csv": csv_path, "json": json_path}
