"""
Estrategia ICT completa integrada con Backtrader.

Implementa el flujo completo del manual:
1. Daily Bias (pre-market) -> determinar dirección
2. Identificar FVGs y liquidez -> encontrar entradas
3. Gestión de posición -> SL/TP/BE/cierre al 90%
4. Kill switches -> protección multinivel
"""
import os
import sys
from datetime import time as dtime, datetime, timedelta
from typing import Optional, List, Dict

import backtrader as bt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import (
    POINT_VALUE, DEFAULT_CONTRACTS,
    BREAK_EVEN_TRIGGER_PCT, CLOSE_AT_PCT_OF_TP,
    MAX_DAILY_LOSS, MAX_TRADES_PER_DAY,
    BIG_LOSS_THRESHOLD, BIG_WIN_THRESHOLD,
    COMMISSION_PER_SIDE, SLIPPAGE_TICKS,
    ACCOUNT_BALANCE, TRAILING_DRAWDOWN_MAX,
    FVG_DUBIOUS_BREAK_PCT, FVG_DUBIOUS_WAIT_BARS,
    DISCOUNT_ZONE_PCT, KILLZONES,
    STRUCTURE_LOOKBACK_4H,
)
from indicators.fvg import (
    FVGType, FVGStatus, FVGTracker, FairValueGap,
    detect_fvgs, filter_significant_fvgs,
)
from indicators.liquidity import (
    LiquidityTracker, LiquidityLevel, LiquidityType, SweepStatus,
    compute_pdh_pdl, find_swing_levels, find_equal_levels,
)
from indicators.market_structure import (
    MarketBias, analyze_4h_trend, detect_swing_points,
    determine_structure, is_move_exhausted, classify_discount_premium,
)
from indicators.structure_engine import StructureEngine, StructureBias
from indicators.liquidity_map import LiquidityMap, LevelSide
from strategy.setup_scorer import SetupScorer, ScoreBreakdown
from risk.position_sizing import PositionSizer
from risk.preflight import preflight_check, PreflightResult
from risk.kill_switch import KillSwitchManager


# =============================================================================
# Comisión personalizada para MNQ
# =============================================================================
class MNQCommInfo(bt.CommInfoBase):
    """Comisión para Micro E-mini Nasdaq 100."""
    params = (
        ("commission", COMMISSION_PER_SIDE),
        ("mult", POINT_VALUE),
        ("margin", 1500.0),      # Margen intradía por contrato
        ("stocklike", False),
        ("commtype", bt.CommInfoBase.COMM_FIXED),
    )

    def _getcommission(self, size, price, pseudoexec):
        return abs(size) * self.p.commission

    def getsize(self, price, cash):
        return int(cash / self.p.margin)


# =============================================================================
# Estrategia ICT Principal
# =============================================================================
class ICTStrategy(bt.Strategy):
    """
    Estrategia de trading ICT mimetizada para backtesting con Backtrader.

    Requiere al menos 2 data feeds:
    - datas[0] : TimeFrame base (1H o 15m)
    - datas[1] : TimeFrame superior (4H, resampled)

    Si hay un 3er feed, se usa como diario.
    """

    params = (
        # Risk management
        ("initial_capital", ACCOUNT_BALANCE),
        ("max_daily_loss", MAX_DAILY_LOSS),
        ("max_trades_per_day", MAX_TRADES_PER_DAY),
        ("default_contracts", DEFAULT_CONTRACTS),
        ("break_even_pct", BREAK_EVEN_TRIGGER_PCT),
        ("close_at_pct", CLOSE_AT_PCT_OF_TP),
        ("big_loss_threshold", BIG_LOSS_THRESHOLD),
        ("big_win_threshold", BIG_WIN_THRESHOLD),

        # ICT parameters
        ("fvg_max_1h", 4),
        ("fvg_search_range", 400),
        ("structure_lookback", STRUCTURE_LOOKBACK_4H),
        ("discount_pct", DISCOUNT_ZONE_PCT),

        # Trading hours (UTC) — 8:30-16:00 VET = 12:30-20:00 UTC
        ("trading_start", dtime(12, 30)),
        ("trading_end", dtime(20, 0)),

        # Logging
        ("verbose", True),
    )

    def __init__(self):
        # Data feeds
        self.data_base = self.datas[0]       # Base TF (1H or 15m)
        self.data_4h = self.datas[1] if len(self.datas) > 1 else None
        self.data_daily = self.datas[2] if len(self.datas) > 2 else None

        # ATR indicator
        # FVG and liquidity trackers
        self.fvg_tracker = FVGTracker(
            dubious_break_pct=FVG_DUBIOUS_BREAK_PCT,
            dubious_wait_bars=FVG_DUBIOUS_WAIT_BARS,
        )
        # Separate FVG tracker for 4H data (higher-TF obstacles / protective FVGs)
        self.fvg_tracker_4h = FVGTracker(
            dubious_break_pct=FVG_DUBIOUS_BREAK_PCT,
            dubious_wait_bars=FVG_DUBIOUS_WAIT_BARS,
        )
        self.liquidity_tracker = LiquidityTracker()

        # New multi-TF modules
        self.structure_engine = StructureEngine(["4h", "base"])
        self.liq_map = LiquidityMap()
        self.scorer = SetupScorer(
            structure_engine=self.structure_engine,
            liq_map=self.liq_map,
            fvg_high=self.fvg_tracker_4h,
            fvg_base=self.fvg_tracker,
        )

        # Risk managers
        self.position_sizer = PositionSizer(
            initial_equity=self.p.initial_capital
        )
        self.kill_switch = KillSwitchManager(
            initial_balance=self.p.initial_capital,
            max_daily_loss=self.p.max_daily_loss,
        )

        # State tracking
        self._current_date = None
        self._daily_bias: Optional[MarketBias] = None   # kept for logging only
        self._bias_confidence: float = 0.0
        self._protective_fvg: Optional[FairValueGap] = None
        self._last_4h_len: int = 0
        self._ny_am_open_set: bool = False
        self._tp_price: Optional[float] = None
        self._sl_price: Optional[float] = None
        self._entry_price: Optional[float] = None
        self._entry_time: Optional[datetime] = None
        self._exit_reason: str = ""
        self._bar_count: int = 0
        self._trades_log: List[Dict] = []
        self._pending_order = None
        self._actual_exit_price: Optional[float] = None
        self._recent_swing_high: Optional[float] = None
        self._recent_swing_low: Optional[float] = None

    def log(self, msg: str, level: str = "INFO"):
        if self.p.verbose:
            dt = self.data_base.datetime.datetime(0)
            print(f"[{dt}] [{level}] {msg}")

    # =========================================================================
    # CONTEXT UPDATE — Ejecutado una vez al inicio de cada día (solo logging)
    # =========================================================================
    def _update_context(self):
        """
        Calcula y loggea el contexto del mercado al inicio de cada día.
        Ya NO bloquea la dirección — el scorer evalúa ambos lados cada barra.
        """
        # Tendencia 4H (solo informativa)
        if self.data_4h is not None and len(self.data_4h) >= self.p.structure_lookback:
            df_4h = pd.DataFrame({
                "Open":  [self.data_4h.open[-i]  for i in range(self.p.structure_lookback - 1, -1, -1)],
                "High":  [self.data_4h.high[-i]  for i in range(self.p.structure_lookback - 1, -1, -1)],
                "Low":   [self.data_4h.low[-i]   for i in range(self.p.structure_lookback - 1, -1, -1)],
                "Close": [self.data_4h.close[-i] for i in range(self.p.structure_lookback - 1, -1, -1)],
            })
            trend_4h = analyze_4h_trend(df_4h, lookback=self.p.structure_lookback)
        else:
            trend_4h = MarketBias.NEUTRAL

        self._daily_bias = trend_4h  # kept for logging / stop() summary only

        broken_bullish = sum(1 for f in self.fvg_tracker.all_fvgs
                             if f.fvg_type == FVGType.BULLISH and f.status == FVGStatus.BROKEN)
        broken_bearish = sum(1 for f in self.fvg_tracker.all_fvgs
                             if f.fvg_type == FVGType.BEARISH and f.status == FVGStatus.BROKEN)

        macro_bias = self.structure_engine.get_macro_bias()
        self.log(
            f"CONTEXT: 4H={trend_4h.value} | engine_macro={macro_bias.value} | "
            f"Bull FVG broken={broken_bullish} | Bear FVG broken={broken_bearish} | "
            f"Upside_exhaust={self.liq_map.upside_exhaustion():.1f}/10 "
            f"Downside_exhaust={self.liq_map.downside_exhaustion():.1f}/10"
        )

    # =========================================================================
    # FVG DETECTION AND TRACKING — Cada barra
    # =========================================================================
    def _update_fvgs(self):
        """Detecta nuevos FVGs y actualiza el estado de los existentes."""
        # Solo si tenemos suficientes barras
        if len(self.data_base) < 3:
            return

        high_2 = self.data_base.high[-2]
        high_0 = self.data_base.high[0]
        low_2 = self.data_base.low[-2]
        low_0 = self.data_base.low[0]

        ts = self.data_base.datetime.datetime(0)

        # Bullish FVG
        if high_2 < low_0:
            fvg = FairValueGap(
                fvg_type=FVGType.BULLISH,
                top=low_0,
                bottom=high_2,
                timestamp=pd.Timestamp(ts),
                timeframe="base",
                candle_idx=self._bar_count,
            )
            self.fvg_tracker.add_fvgs([fvg])

        # Bearish FVG
        if low_2 > high_0:
            fvg = FairValueGap(
                fvg_type=FVGType.BEARISH,
                top=low_2,
                bottom=high_0,
                timestamp=pd.Timestamp(ts),
                timeframe="base",
                candle_idx=self._bar_count,
            )
            self.fvg_tracker.add_fvgs([fvg])

        # Actualizar estado de FVGs existentes
        self.fvg_tracker.update(
            self.data_base.high[0],
            self.data_base.low[0],
            self.data_base.close[0],
        )

        # Alimentar structure engine con la vela cerrada del base TF
        self.structure_engine.update(
            "base",
            self.data_base.open[0],
            self.data_base.high[0],
            self.data_base.low[0],
            self.data_base.close[0],
            ts,
        )

    # =========================================================================
    # LIQUIDITY TRACKING — Cada barra
    # =========================================================================
    def _update_liquidity(self):
        """Actualiza niveles de liquidez y detecta sweeps."""
        if len(self.data_base) < 10:
            return

        price = self.data_base.close[0]
        ts = pd.Timestamp(self.data_base.datetime.datetime(0))

        price = self.data_base.close[0]
        high  = self.data_base.high[0]
        low   = self.data_base.low[0]

        # Actualizar sweeps (tracker legacy)
        self.liquidity_tracker.update(high, low, price, ts)

        # Actualizar liquidity map con la vela cerrada
        self.liq_map.update(high, low, price, ts)

        # Establecer apertura de NY AM para rango de proximidad
        if not self._ny_am_open_set and self._get_current_session() == "ny_am":
            self.liq_map.set_ny_am_open(price)
            self._ny_am_open_set = True

        # Actualizar swing points y equal levels cada 10 barras
        if self._bar_count % 10 == 0:
            lookback = min(50, len(self.data_base))
            df_mini = pd.DataFrame({
                "High": [self.data_base.high[-i] for i in range(lookback - 1, -1, -1)],
                "Low":  [self.data_base.low[-i]  for i in range(lookback - 1, -1, -1)],
            })

            swing_highs, swing_lows = find_swing_levels(df_mini, order=3, lookback=lookback)
            self.liquidity_tracker.add_levels(swing_highs + swing_lows)

            # Swings al liquidity map
            for sh in swing_highs:
                self.liq_map.add_swing(sh.price, LevelSide.ABOVE, ts)
            for sl in swing_lows:
                self.liq_map.add_swing(sl.price, LevelSide.BELOW, ts)

            # Equal Highs / Equal Lows → peso 8 (misma jerarquía que LRLR)
            for eq in find_equal_levels(df_mini, "High", lookback=lookback):
                self.liq_map.add_equal_level(eq.price, LevelSide.ABOVE, ts,
                                             touches=getattr(eq, "touches", 2))
            for eq in find_equal_levels(df_mini, "Low", lookback=lookback):
                self.liq_map.add_equal_level(eq.price, LevelSide.BELOW, ts,
                                             touches=getattr(eq, "touches", 2))

            # Track recent swings para discount/premium
            if swing_highs:
                self._recent_swing_high = swing_highs[-1].price
            if swing_lows:
                self._recent_swing_low = swing_lows[-1].price

        # Actualizar tracker de 4H cuando llega nueva vela de 4H
        if self.data_4h is not None and len(self.data_4h) > self._last_4h_len:
            self._last_4h_len = len(self.data_4h)
            if len(self.data_4h) >= 3:
                h2_4h = self.data_4h.high[-2]
                h0_4h = self.data_4h.high[0]
                l2_4h = self.data_4h.low[-2]
                l0_4h = self.data_4h.low[0]
                ts_4h = pd.Timestamp(self.data_4h.datetime.datetime(0))
                if h2_4h < l0_4h:
                    self.fvg_tracker_4h.add_fvgs([FairValueGap(
                        fvg_type=FVGType.BULLISH, top=l0_4h, bottom=h2_4h,
                        timestamp=ts_4h, timeframe="4h", candle_idx=self._last_4h_len,
                    )])
                if l2_4h > h0_4h:
                    self.fvg_tracker_4h.add_fvgs([FairValueGap(
                        fvg_type=FVGType.BEARISH, top=l2_4h, bottom=h0_4h,
                        timestamp=ts_4h, timeframe="4h", candle_idx=self._last_4h_len,
                    )])
            self.fvg_tracker_4h.update(
                self.data_4h.high[0], self.data_4h.low[0], self.data_4h.close[0]
            )
            self.structure_engine.update(
                "4h",
                self.data_4h.open[0], self.data_4h.high[0],
                self.data_4h.low[0],  self.data_4h.close[0],
                pd.Timestamp(self.data_4h.datetime.datetime(0)),
            )

        # PDH/PDL — al inicio de nuevo día
        current_date = self.data_base.datetime.date(0)
        if self._current_date != current_date and len(self.data_base) >= 24:
            prev_high = -np.inf
            prev_low = np.inf
            for i in range(1, min(25, len(self.data_base))):
                bar_date = self.data_base.datetime.date(-i)
                if bar_date != current_date:
                    prev_high = max(prev_high, self.data_base.high[-i])
                    prev_low = min(prev_low, self.data_base.low[-i])
                elif prev_high > -np.inf:
                    break

            if prev_high > -np.inf:
                self.liquidity_tracker.add_levels([
                    LiquidityLevel(LiquidityType.PDH, prev_high, ts,
                                   f"PDH {prev_high:.0f}"),
                    LiquidityLevel(LiquidityType.PDL, prev_low, ts,
                                   f"PDL {prev_low:.0f}"),
                ])
                # También al liquidity map
                self.liq_map.add_pdh_pdl(prev_high, prev_low, ts)
                self.liq_map.reset_intraday()
                self._ny_am_open_set = False

    # =========================================================================
    # ENTRY LOGIC — Buscar oportunidades
    # =========================================================================
    # =========================================================================
    # SESSION / KILLZONE HELPERS
    # =========================================================================
    def _get_current_session(self) -> Optional[str]:
        """
        Return the KILLZONES key matching the current bar's ET time, or None.
        Backtrader feeds from yfinance for NQ=F are in Eastern Time (ET).
        """
        dt = self.data_base.datetime.datetime(0)
        current_time = dt.time()

        for key, zone in KILLZONES.items():
            sh, sm = map(int, zone.start_et.split(":"))
            eh, em = map(int, zone.end_et.split(":"))
            zone_start = dtime(sh, sm)
            zone_end = dtime(eh, em)

            # Standard window: start <= t < end
            if zone_start < zone_end:
                if zone_start <= current_time < zone_end:
                    return key
                continue

            # Overnight window (wrap midnight): t >= start OR t < end
            if current_time >= zone_start or current_time < zone_end:
                return key
        return None

    # =========================================================================
    # ENTRY LOGIC — Scorer-based, evaluates BOTH sides every bar
    # =========================================================================
    def _check_entry(self):
        """
        Evalúa long Y short cada barra usando el SetupScorer.
        No hay lock de dirección — el scorer decide basándose en
        la suma de ingredientes ICT (sweep + CHoCH + FVG path + targets).
        """
        if self.position:
            return

        if self._pending_order is not None:
            return

        # Solo durante NY AM killzone
        if self._get_current_session() != "ny_am":
            return

        can_trade, _ = self.kill_switch.can_open_trade()
        if not can_trade:
            return

        price = self.data_base.close[0]
        self.scorer.set_bar(self._bar_count)
        setup = self.scorer.best_setup(price, self.kill_switch.trades_today)

        if setup is not None:
            self._execute_entry(setup, price)

    def _execute_entry(self, setup: ScoreBreakdown, price: float):
        """Ejecuta una entrada basada en el ScoreBreakdown del scorer."""
        if setup.protective_fvg is None or setup.target_level is None:
            return

        direction = setup.direction
        if direction == "long":
            sl_price = setup.protective_fvg.bottom
            tp_price = setup.target_level.price
            sl_points = price - sl_price
            tp_points = tp_price - price
        else:
            sl_price = setup.protective_fvg.top
            tp_price = setup.target_level.price
            sl_points = sl_price - price
            tp_points = price - tp_price

        if sl_points <= 0 or tp_points <= 0:
            return

        num_contracts = self.position_sizer.get_position_size(sl_points)
        ks_max = self.kill_switch.get_max_contracts()
        if ks_max is not None:
            num_contracts = min(num_contracts, ks_max)
        if num_contracts <= 0:
            return

        pf = preflight_check(
            entry_price=price,
            stop_loss_price=sl_price,
            take_profit_price=tp_price,
            num_contracts=num_contracts,
            direction=direction,
            current_daily_pnl=self.kill_switch.daily_pnl,
            trades_today=self.kill_switch.trades_today,
            current_drawdown=self.kill_switch.current_drawdown,
        )

        if not pf.passed:
            self.log(f"{direction.upper()} RECHAZADO: {pf.summary}", "WARN")
            return

        self.log(
            f"-> {direction.upper()} ENTRY @ {price:.1f} | SL={sl_price:.1f} | "
            f"TP={tp_price:.1f} | Contracts={num_contracts} | "
            f"R:R={tp_points/sl_points:.2f}:1 | Score={setup.total_score:.1f}"
        )
        self.log(f"   Razones: {' | '.join(setup.reasons[:5])}")

        self._entry_price = price
        self._sl_price = sl_price
        self._tp_price = tp_price
        self._entry_time = self.data_base.datetime.datetime(0)
        self._exit_reason = ""
        self._protective_fvg = setup.protective_fvg

        if direction == "long":
            self._pending_order = self.buy(size=num_contracts)
        else:
            self._pending_order = self.sell(size=num_contracts)

    # =========================================================================
    # EXIT / POSITION MANAGEMENT — Cada barra durante un trade abierto
    # =========================================================================
    def _manage_position(self):
        """
        Gestión de posición abierta:
        1. Check SL/TP
        2. Break even al 50% del TP si el precio gira
        3. Cierre al 90% del TP
        4. Ruptura del FVG protector -> salir
        """
        if not self.position or self._entry_price is None:
            return

        price = self.data_base.close[0]
        high = self.data_base.high[0]
        low = self.data_base.low[0]
        size = self.position.size

        is_long = size > 0

        if is_long:
            unrealized_pnl = (price - self._entry_price) * POINT_VALUE * abs(size)
            tp_total = (self._tp_price - self._entry_price) * POINT_VALUE * abs(size)
        else:
            unrealized_pnl = (self._entry_price - price) * POINT_VALUE * abs(size)
            tp_total = (self._entry_price - self._tp_price) * POINT_VALUE * abs(size)

        # --- CHECK 1: Stop Loss ---
        if is_long and low <= self._sl_price:
            self.log(f"X SL HIT (LONG) @ ~{self._sl_price:.1f}", "EXIT")
            self.close()
            return
        elif not is_long and high >= self._sl_price:
            self.log(f"X SL HIT (SHORT) @ ~{self._sl_price:.1f}", "EXIT")
            self.close()
            return

        # --- CHECK 2: Take Profit completo ---
        if is_long and high >= self._tp_price:
            self.log(f"OK TP HIT (LONG) @ ~{self._tp_price:.1f}", "EXIT")
            self.close()
            return
        elif not is_long and low <= self._tp_price:
            self.log(f"OK TP HIT (SHORT) @ ~{self._tp_price:.1f}", "EXIT")
            self.close()
            return

        # --- CHECK 3: Cierre al 90% del TP ---
        if tp_total > 0 and unrealized_pnl >= tp_total * self.p.close_at_pct:
            self.log(
                f"OK 90% TP alcanzado: ${unrealized_pnl:.0f} / ${tp_total:.0f}", "EXIT"
            )
            self.close()
            return

        # --- CHECK 4: Break Even ---
        if tp_total > 0 and unrealized_pnl >= tp_total * self.p.break_even_pct:
            # ¿El precio está girando?  Check si FVGs a favor se están rompiendo
            # Note: fvg_tracker.update() was already called in _update_fvgs() this bar
            if self._protective_fvg is not None:
                if is_long:
                    # Si Bullish FVGs de soporte se rompen -> BE
                    supporting_broken = any(
                        f.fvg_type == FVGType.BULLISH
                        and f.status == FVGStatus.BROKEN
                        and f.candle_idx > self._bar_count - 5
                        for f in self.fvg_tracker.all_fvgs
                    )
                else:
                    supporting_broken = any(
                        f.fvg_type == FVGType.BEARISH
                        and f.status == FVGStatus.BROKEN
                        and f.candle_idx > self._bar_count - 5
                        for f in self.fvg_tracker.all_fvgs
                    )

                if supporting_broken:
                    self.log(
                        f"<> BREAK EVEN @ {unrealized_pnl:.0f} — FVGs de soporte rotos", "EXIT"
                    )
                    self._exit_reason = "Break Even"
                    self.close()
                    return

        # --- CHECK 5: Ruptura del FVG protector ("en seco") ---
        if self._protective_fvg is not None and self._protective_fvg.status == FVGStatus.BROKEN:
            self.log(
                f"X FVG PROTECTOR ROTO ({self._protective_fvg.fvg_type.value}) — salir", "EXIT"
            )
            self._exit_reason = "FVG Protector Roto"
            self.close()
            return

    # =========================================================================
    # TRADING HOURS CHECK — NYSE Open + VET Forced Close
    # =========================================================================
    def _is_trading_hours(self) -> bool:
        """
        Check if current time is within allowed trading hours.

        Rules:
        - Opens: 9:30 AM ET (NYSE market open)
        - Force close: 4:00 PM VET (UTC-4) — fixed, no DST

        Since Backtrader data is in ET timezone:
        - NYSE open = 9:30 AM ET (always)
        - VET close at 4:00 PM VET (UTC-4):
          * During EDT (ET=UTC-4): 4:00 PM VET = 4:00 PM ET
          * During EST (ET=UTC-5): 4:00 PM VET = 3:00 PM ET

        We compute the ET-equivalent of 4:00 PM VET dynamically.
        """
        dt = self.data_base.datetime.datetime(0)
        current_time = dt.time()

        # NYSE opens at 9:30 AM ET regardless of DST
        nyse_open = dtime(9, 30)

        # Calculate forced close time in ET
        # VET is always UTC-4. ET is UTC-5 (EST) or UTC-4 (EDT).
        # Force close = 4:00 PM VET = 20:00 UTC
        # In ET: if EDT (UTC-4) -> 20:00 - 4 = 16:00 ET
        #        if EST (UTC-5) -> 20:00 - 5 = 15:00 ET
        force_close_et = self._get_vet_close_in_et(dt)

        return nyse_open <= current_time <= force_close_et

    def _get_vet_close_in_et(self, dt: datetime) -> dtime:
        """
        Convert 4:00 PM VET (UTC-4) to Eastern Time equivalent.

        VET is always UTC-4 (no DST).
        ET switches between UTC-5 (EST, Nov-Mar) and UTC-4 (EDT, Mar-Nov).

        4:00 PM VET = 20:00 UTC
        - During EDT: 20:00 - 4 = 16:00 ET
        - During EST: 20:00 - 5 = 15:00 ET
        """
        try:
            import pytz
            et_tz = pytz.timezone('US/Eastern')
            # Make dt timezone-aware in ET
            dt_aware = et_tz.localize(dt)
            # Get UTC offset in hours
            utc_offset_hours = dt_aware.utcoffset().total_seconds() / 3600
            # VET close is 20:00 UTC -> convert to ET
            force_close_utc_hour = 20  # 4:00 PM VET = 20:00 UTC
            force_close_et_hour = force_close_utc_hour + int(utc_offset_hours)
            return dtime(force_close_et_hour, 0)
        except ImportError:
            # Fallback: assume EST (conservative, closes earlier)
            return dtime(15, 0)

    def _should_force_close(self) -> bool:
        """
        Check if we must force-close all positions.
        Returns True if current time >= 4:00 PM VET (in ET equivalent).
        Called every bar when position is open.
        """
        dt = self.data_base.datetime.datetime(0)
        current_time = dt.time()
        force_close_et = self._get_vet_close_in_et(dt)

        # Force close 5 minutes before deadline to ensure execution
        close_min = force_close_et.hour * 60 + force_close_et.minute - 5
        close_warning = dtime(close_min // 60, close_min % 60)

        return current_time >= close_warning

    # =========================================================================
    # MAIN LOOP — next() de Backtrader
    # =========================================================================
    def next(self):
        """Método principal ejecutado en cada barra."""
        self._bar_count += 1

        # Solo operar en días de semana
        current_dt = self.data_base.datetime.datetime(0)
        if current_dt.weekday() >= 5:
            return

        # Actualizar FVGs y liquidez
        self._update_fvgs()
        self._update_liquidity()

        # Nuevo día -> actualizar contexto (sin lock de dirección)
        current_date = current_dt.date()
        if self._current_date != current_date:
            self._current_date = current_date
            self.kill_switch.new_day(current_date)
            self._update_context()
            self.fvg_tracker.cleanup_old()
            self.fvg_tracker_4h.cleanup_old()

        # Forced close check: 4:00 PM VET (UTC-4) — no exceptions
        if self.position and self._should_force_close():
            self.log(
                f"FORCED CLOSE at VET 4:00 PM deadline | "
                f"ET time: {current_dt.time()}",
                "EXIT"
            )
            self._exit_reason = "Forced Close (VET 4PM)"
            self.close()
            return

        # ── Session-based close: force close on NY Lunch entry (12:00 ET) ───
        if self.position:
            _sk = self._get_current_session()
            _kz = KILLZONES.get(_sk) if _sk else None
            if _kz is not None and _kz.close_on_enter:
                self.log(
                    f"FORCED CLOSE: {_kz.name} killzone ({_kz.start_et} ET)",
                    "EXIT",
                )
                self._exit_reason = f"Session Close ({_kz.name})"
                self.close()
                return

        # Check if within NYSE trading hours (9:30 ET - close)
        if not self._is_trading_hours():
            # Outside hours: do not open new positions
            if self.position:
                # Still manage existing position (SL/TP) even outside hours
                self._manage_position()
            return

        # Within trading hours: manage or seek entry
        if self.position:
            self._manage_position()
        else:
            # Do not open new positions if we're in the 5-min forced-close buffer
            if not self._should_force_close():
                self._check_entry()

    # =========================================================================
    # ORDER NOTIFICATIONS
    # =========================================================================
    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"COMPRA EJECUTADA @ {order.executed.price:.1f} | "
                    f"Size={order.executed.size} | Cost=${order.executed.comm:.2f}",
                    "ORDER"
                )
            else:
                self.log(
                    f"VENTA EJECUTADA @ {order.executed.price:.1f} | "
                    f"Size={order.executed.size} | Cost=${order.executed.comm:.2f}",
                    "ORDER"
                )
            # Capture actual fill price for exit trades (position closed after this)
            if self._entry_price is not None and not self.position:
                self._actual_exit_price = order.executed.price
            self._pending_order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Orden {order.status}: cancelada/rechazada", "WARN")
            self._pending_order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            pnl = trade.pnl
            pnl_net = trade.pnlcomm

            self.log(
                f"{'WIN' if pnl_net > 0 else 'LOSS'}: "
                f"Gross=${pnl:.2f} | Net=${pnl_net:.2f} | "
                f"Comm=${trade.commission:.2f}",
                "TRADE"
            )

            # Registrar en los managers de riesgo
            self.position_sizer.record_trade(pnl_net)
            self.kill_switch.record_trade(pnl_net)

            # Log del trade
            self._trades_log.append({
                "timestamp": self.data_base.datetime.datetime(0),
                "direction": "long" if trade.long else "short",
                "entry_price": self._entry_price,
                "exit_price": self._actual_exit_price if self._actual_exit_price is not None else self.data_base.close[0],
                "sl_price": self._sl_price,
                "tp_price": self._tp_price,
                "pnl_gross": pnl,
                "pnl_net": pnl_net,
                "commission": trade.commission,
                "contracts": abs(trade.size),
                "reason": self._exit_reason or "Manual",
                "entry_time": self._entry_time,
                "exit_time": self.data_base.datetime.datetime(0),
            })

            # Reset state
            self._entry_price = None
            self._sl_price = None
            self._tp_price = None
            self._entry_time = None
            self._exit_reason = ""
            self._protective_fvg = None
            self._actual_exit_price = None

    # =========================================================================
    # STOP — Llamado al finalizar el backtest
    # =========================================================================
    def stop(self):
        """Genera resumen al finalizar."""
        total_trades = len(self._trades_log)
        if total_trades == 0:
            self.log("=" * 50)
            self.log("SIN TRADES EJECUTADOS")
            self.log("=" * 50)
            return

        wins = [t for t in self._trades_log if t["pnl_net"] > 0]
        losses = [t for t in self._trades_log if t["pnl_net"] <= 0]

        total_pnl = sum(t["pnl_net"] for t in self._trades_log)
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        avg_win = np.mean([t["pnl_net"] for t in wins]) if wins else 0
        avg_loss = np.mean([t["pnl_net"] for t in losses]) if losses else 0

        self.log("=" * 60)
        self.log("RESUMEN DE BACKTESTING")
        self.log("=" * 60)
        self.log(f"Total trades:    {total_trades}")
        self.log(f"Wins/Losses:     {len(wins)}/{len(losses)}")
        self.log(f"Win Rate:        {win_rate:.1%}")
        self.log(f"P&L Total:       ${total_pnl:+,.2f}")
        self.log(f"Avg Win:         ${avg_win:+,.2f}")
        self.log(f"Avg Loss:        ${avg_loss:+,.2f}")
        self.log(f"Profit Factor:   {abs(sum(t['pnl_net'] for t in wins)) / abs(sum(t['pnl_net'] for t in losses)):.2f}" if losses and sum(t['pnl_net'] for t in losses) != 0 else "Profit Factor:   N/A")
        self.log(f"Final Balance:   ${self.broker.getvalue():,.2f}")
        self.log(f"Max Drawdown:    ${self.kill_switch.current_drawdown:,.2f}")
        self.log("=" * 60)

    def get_trades_df(self) -> pd.DataFrame:
        """Retorna los trades como DataFrame para análisis posterior."""
        if not self._trades_log:
            return pd.DataFrame()
        return pd.DataFrame(self._trades_log)
