"""
FastAPI HTTP server — frontend bridge for the ICT trading bot.

This module is a thin wrapper over the existing backtest pipeline:
  Frontend (Next.js)  ──HTTP──▶  this server  ──calls──▶  backtest.run_backtest()

It does NOT duplicate, replace, or modify any strategy logic. The trading
behavior remains 100% defined by:
  - strategy/ict_strategy.py
  - indicators/*.py
  - risk/*.py
  - config/settings.py

Run locally:
    uvicorn server:app --reload --port 8000

Run in production (VPS, behind nginx):
    uvicorn server:app --host 127.0.0.1 --port 8000 --workers 1
"""
from __future__ import annotations

import logging
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Make the project root importable so we can use the existing modules untouched.
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from api_server.schemas import BacktestRequest, BacktestResultOut
from api_server.serializers import assemble_backtest_result

# Existing project modules — IMPORT-ONLY, NOT MODIFIED.
from data.downloader import download_data, resample_ohlcv
from backtest import run_backtest


# =============================================================================
# Logging
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("tradingbot.api")


# =============================================================================
# App
# =============================================================================
app = FastAPI(
    title="ICT Trading Bot API",
    description=(
        "HTTP bridge between the Next.js dashboard and the Python ICT "
        "strategy. Wraps backtest.run_backtest() — does not implement any "
        "trading logic of its own."
    ),
    version="1.0.0",
)

# CORS — allow the frontend (running on the same VPS or remote) to call us.
# In production you can replace ["*"] with the explicit dashboard origin.
_allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
_allowed_origins = (
    ["*"] if _allowed_origins_env.strip() == "*"
    else [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# =============================================================================
# Health
# =============================================================================
@app.get("/health")
def health() -> dict:
    """
    Liveness probe. Used by nginx / systemd / curl to verify the server
    is up. Does NOT touch the strategy or download data.
    """
    return {
        "status": "ok",
        "service": "tradingbot-api",
        "time": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/")
def root() -> dict:
    return {
        "service": "ICT Trading Bot API",
        "endpoints": ["/health", "/backtest"],
    }


# =============================================================================
# Backtest
# =============================================================================
@app.post("/backtest", response_model=BacktestResultOut)
def post_backtest(req: BacktestRequest) -> dict:
    """
    Run a backtest with the user-provided config and date range.

    Wire format matches lib/types.ts on the frontend exactly:
      Request body  → BacktestRequest
      Response body → BacktestResult (subset of BacktestResultOut)

    Pipeline:
      1. download_data() pulls historical OHLC from yfinance (with cache).
      2. run_backtest() runs the Backtrader/ICTStrategy pipeline unchanged.
      3. assemble_backtest_result() reshapes the output into JSON.
    """
    t0 = time.time()
    log.info(
        "POST /backtest %s → %s @ %s | preset=%s",
        req.start_date, req.end_date, req.interval, req.config.name,
    )

    # ---------- 1. Download historical data --------------------------------
    try:
        df_base = download_data(
            interval=req.interval,
            start=req.start_date,
            end=req.end_date,
        )
    except Exception as e:
        log.exception("Data download failed")
        raise HTTPException(
            status_code=502,
            detail=f"No se pudieron descargar datos del mercado: {e}",
        )

    if df_base is None or df_base.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                f"yfinance no devolvió datos para {req.interval} entre "
                f"{req.start_date} y {req.end_date}. "
                f"Recuerda: 5m/15m solo cubren los últimos 60 días, "
                f"1h cubre hasta 730 días."
            ),
        )

    # Optional intraday feeds — only attached if available (recent dates)
    df_15m: Optional[object] = None
    df_5m: Optional[object] = None
    if req.interval in ("1h", "15m"):
        try:
            _df_15m = download_data(interval="15m")
            if _df_15m is not None and not _df_15m.empty:
                df_15m = _df_15m
        except Exception as e:
            log.warning("Could not fetch 15m feed: %s", e)
        try:
            _df_5m = download_data(interval="5m")
            if _df_5m is not None and not _df_5m.empty:
                df_5m = _df_5m
        except Exception as e:
            log.warning("Could not fetch 5m feed: %s", e)

    # ---------- 2. Map the frontend BotConfig to ICTStrategy params --------
    # Only fields the strategy currently exposes as Backtrader params are
    # forwarded. Extra fields (e.g. fvg_lookback_*) are accepted on the wire
    # but skipped here so we don't accidentally pass unknown kwargs.
    cfg = req.config
    strategy_params = {
        "initial_capital":      cfg.initial_capital,
        "max_daily_loss":       cfg.max_daily_loss,
        "max_trades_per_day":   cfg.max_trades_per_day,
        "default_contracts":    cfg.default_contracts,
        "break_even_pct":       cfg.break_even_pct,
        "close_at_pct":         cfg.close_at_pct,
        "big_loss_threshold":   cfg.big_loss_threshold,
        "big_win_threshold":    cfg.big_win_threshold,
        "fvg_max_1h":           cfg.fvg_max_1h,
        "fvg_search_range":     cfg.fvg_search_range,
        "structure_lookback":   cfg.structure_lookback,
        "verbose":              False,
    }

    # ---------- 3. Run the backtest ----------------------------------------
    try:
        result = run_backtest(
            df=df_base,
            period_name=f"{req.start_date} → {req.end_date}",
            initial_capital=cfg.initial_capital,
            verbose=False,
            plot=False,
            strategy_params=strategy_params,
            df_15m=df_15m,
            df_5m=df_5m,
        )
    except Exception as e:
        log.error("Backtest crashed:\n%s", traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"El backtest falló: {e}",
        )

    # ---------- 4. Assemble the response ----------------------------------
    # Build optional ohlc_by_timeframe so the chart's TF switcher works.
    ohlc_by_timeframe = {req.interval: df_base}
    if req.interval == "1h":
        try:
            ohlc_by_timeframe["4h"] = resample_ohlcv(df_base, "4h")
        except Exception as e:
            log.warning("Could not resample to 4h: %s", e)
    if df_15m is not None:
        ohlc_by_timeframe["15m"] = df_15m
    if df_5m is not None:
        ohlc_by_timeframe["5m"] = df_5m

    payload = assemble_backtest_result(
        backtest_id=f"bt-{int(time.time())}",
        period_name=f"{req.start_date} → {req.end_date}",
        request_config=req.config.model_dump(),
        metrics=result["metrics"],
        trades_df=result["trades_df"],
        df_ohlc=result["df_ohlc"],
        indicator_state=result.get("indicator_state", {}),
        start_date=req.start_date,
        ohlc_by_timeframe=ohlc_by_timeframe,
    )

    log.info(
        "POST /backtest done in %.1fs | %d trades | final $%.2f",
        time.time() - t0,
        payload["metrics"]["total_trades"],
        payload["metrics"]["final_balance"],
    )
    return payload


# =============================================================================
# Catch-all error handler — keeps the JSON contract with the frontend
# =============================================================================
@app.exception_handler(Exception)
async def _unhandled_exception(_, exc: Exception):
    log.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": exc.__class__.__name__},
    )
