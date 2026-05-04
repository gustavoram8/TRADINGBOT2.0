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

import asyncio
import json as _json
import logging
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, date as date_type
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

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
# Backtest — synchronous pipeline (runs in a thread pool worker)
# =============================================================================
def _pipeline_sync(req: BacktestRequest) -> dict:
    """
    Full download + backtest + serialization pipeline, executed in a thread
    so the async endpoint can stream keepalive bytes while this runs.

    Returns the assembled payload dict on success.
    Raises HTTPException on known errors (propagated by the async wrapper).
    """
    # Auto-select finest available TF based on date range.
    _start = datetime.strptime(req.start_date, "%Y-%m-%d").date()
    _end   = datetime.strptime(req.end_date,   "%Y-%m-%d").date()
    _days  = (_end - _start).days
    interval = "15m" if _days <= 58 else "1h"

    t0 = time.time()
    log.info(
        "POST /backtest %s → %s (auto-TF=%s, %d days) | preset=%s",
        req.start_date, req.end_date, interval, _days, req.config.name,
    )

    # ---------- 1. Download historical data (all feeds in parallel) ----------
    _DOWNLOAD_TIMEOUT = 55

    def _fetch(iv: str, start: Optional[str] = None, end: Optional[str] = None):
        try:
            return download_data(interval=iv, start=start, end=end)
        except Exception as exc:
            return exc

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_base = pool.submit(_fetch, interval, req.start_date, req.end_date)
        f_15m  = pool.submit(_fetch, "15m") if interval != "15m" else None
        f_5m   = pool.submit(_fetch, "5m")

        try:
            _res_base = f_base.result(timeout=_DOWNLOAD_TIMEOUT)
        except FuturesTimeoutError:
            raise HTTPException(status_code=504,
                detail=f"Timeout descargando datos {interval}. Intenta de nuevo.")
        if isinstance(_res_base, Exception):
            log.exception("Data download failed: %s", _res_base)
            raise HTTPException(status_code=502,
                detail=f"No se pudieron descargar datos del mercado: {_res_base}")
        df_base = _res_base

        df_15m: Optional[object] = None
        df_5m:  Optional[object] = None
        if f_15m is not None:
            try:
                _r15 = f_15m.result(timeout=_DOWNLOAD_TIMEOUT)
                if not isinstance(_r15, Exception) and _r15 is not None and not _r15.empty:
                    df_15m = _r15
                elif isinstance(_r15, Exception):
                    log.warning("Could not fetch 15m feed: %s", _r15)
            except FuturesTimeoutError:
                log.warning("15m feed download timed out — skipped")
        try:
            _r5 = f_5m.result(timeout=_DOWNLOAD_TIMEOUT)
            if not isinstance(_r5, Exception) and _r5 is not None and not _r5.empty:
                df_5m = _r5
            elif isinstance(_r5, Exception):
                log.warning("Could not fetch 5m feed: %s", _r5)
        except FuturesTimeoutError:
            log.warning("5m feed download timed out — skipped")

    # Fallback: 15m returned no data (date range older than 60 days)
    if (df_base is None or df_base.empty) and interval == "15m":
        log.warning(
            "15m returned no data for %s→%s — falling back to 1h",
            req.start_date, req.end_date,
        )
        interval = "1h"
        try:
            df_base = download_data(interval="1h", start=req.start_date, end=req.end_date)
        except Exception as e:
            raise HTTPException(status_code=502,
                detail=f"No se pudieron descargar datos del mercado: {e}")

    if df_base is None or df_base.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                f"yfinance no devolvió datos entre "
                f"{req.start_date} y {req.end_date}. "
                f"El rango máximo para 1h es 730 días."
            ),
        )

    # ---------- 2. Map frontend BotConfig → ICTStrategy params ---------------
    cfg = req.config
    strategy_params = {
        "initial_capital":      cfg.initial_capital,
        "max_daily_loss":       cfg.max_daily_loss,
        "max_trades_per_day":   cfg.max_trades_per_day,
        "default_contracts":    cfg.default_contracts,
        "max_loss_per_trade":   cfg.max_loss_per_trade,
        "break_even_pct":       cfg.break_even_pct,
        "close_at_pct":         cfg.close_at_pct,
        "big_loss_threshold":   cfg.big_loss_threshold,
        "big_win_threshold":    cfg.big_win_threshold,
        "fvg_max_1h":           cfg.fvg_max_1h,
        "fvg_search_range":     cfg.fvg_search_range,
        "structure_lookback":   cfg.structure_lookback,
        "verbose":              False,
    }

    # ---------- 3. Run the backtest ------------------------------------------
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
            base_tf=interval,
        )
    except Exception as e:
        log.error("Backtest crashed:\n%s", traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"El backtest falló: {e}",
        )

    # ---------- 4. Assemble response -----------------------------------------
    ohlc_by_timeframe = {interval: df_base}
    try:
        ohlc_by_timeframe["4h"] = resample_ohlcv(df_base, "4h")
    except Exception as e:
        log.warning("Could not resample to 4h: %s", e)
    if interval == "15m":
        try:
            ohlc_by_timeframe["1h"] = resample_ohlcv(df_base, "1h")
        except Exception as e:
            log.warning("Could not resample to 1h: %s", e)
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
        rejection_counts=result.get("rejection_counts", {}),
    )

    log.info(
        "POST /backtest done in %.1fs | %d trades | final $%.2f",
        time.time() - t0,
        payload["metrics"]["total_trades"],
        payload["metrics"]["final_balance"],
    )
    return payload


# =============================================================================
# Backtest endpoint — async streaming wrapper
# =============================================================================
@app.post("/backtest")
async def post_backtest(req: BacktestRequest):
    """
    Streaming endpoint: runs the backtest pipeline in a thread while sending
    newline keepalive bytes every 5 seconds so the Node.js fetch() in the
    Next.js server never times out waiting for the first response byte.
    The final JSON payload is sent as the last chunk.

    Error handling: errors are embedded in the JSON body with an "error" key
    (and optional "__status" key) since we can't change the HTTP status code
    after streaming has begun.
    """
    loop = asyncio.get_event_loop()
    done: asyncio.Event = asyncio.Event()
    result_box: dict = {}

    async def _run():
        try:
            payload = await loop.run_in_executor(None, _pipeline_sync, req)
            result_box["ok"] = payload
        except HTTPException as exc:
            result_box["http_err"] = {"status": exc.status_code, "detail": exc.detail}
        except Exception as exc:
            log.error("Unhandled pipeline error:\n%s", traceback.format_exc())
            result_box["err"] = str(exc)
        finally:
            done.set()

    asyncio.create_task(_run())

    async def keepalive_stream():
        # Send a newline every 5 seconds while the pipeline runs.
        # This keeps the TCP connection alive and prevents Node.js undici
        # from firing its headersTimeout (~30 s by default).
        while not done.is_set():
            yield b"\n"
            try:
                await asyncio.wait_for(asyncio.shield(done.wait()), timeout=5.0)
            except asyncio.TimeoutError:
                pass

        # Pipeline finished — send the result JSON as the final chunk.
        if "http_err" in result_box:
            err = result_box["http_err"]
            yield _json.dumps(
                {"error": err["detail"], "__status": err["status"]}
            ).encode()
        elif "err" in result_box:
            yield _json.dumps({"error": result_box["err"]}).encode()
        else:
            yield _json.dumps(result_box["ok"]).encode()

    return StreamingResponse(keepalive_stream(), media_type="application/json")


# =============================================================================
# Catch-all error handler
# =============================================================================
@app.exception_handler(Exception)
async def _unhandled_exception(_, exc: Exception):
    log.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": exc.__class__.__name__},
    )
