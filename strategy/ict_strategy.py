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
    MAX_DAILY_LOSS, MAX_TRADES_PER_DAY, MAX_LOSS_PER_TRADE,
    BIG_LOSS_THRESHOLD, BIG_WIN_THRESHOLD,
    COMMISSION_PER_SIDE, SLIPPAGE_TICKS,
    ACCOUNT_BALANCE, TRAILING_DRAWDOWN_MAX,
    FVG_DUBIOUS_BREAK_PCT, FVG_DUBIOUS_WAIT_BARS,
    DISCOUNT_ZONE_PCT, KILLZONES,
    STRUCTURE_LOOKBACK_4H,
    SCORER_MIN_SCORE_TRADE_1, SCORER_MIN_SCORE_TRADE_2,
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
        ("trailing_drawdown_max", TRAILING_DRAWDOWN_MAX),
        ("max_trades_per_day", MAX_TRADES_PER_DAY),
        ("default_contracts", DEFAULT_CONTRACTS),
        ("max_loss_per_trade", MAX_LOSS_PER_TRADE),
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

        # Cooldown (in base-TF bars) after a losing trade closes — prevents
        # over-reactive flips per user's risk rule.
        ("loss_cooldown_bars", 3),

        # Phase 6.3 — minimum trades expected per rolling 7-day window;
        # below this we log a ⚠ TRADE PACE warning (no auto-action).
        ("pace_warn_threshold_7d", 3),

        # Phase 6.4 — opt-in granular 5m scoring log during NY AM.
        # Only emits when the leading direction flips OR a score crosses
        # the per-trade threshold; never spammy.
        ("verbose_5m", False),

        # Logging
        ("verbose", True),
    )

    def __init__(self):
        # Data feeds
        self.data_base = self.datas[0]
        self.data_4h = self.datas[1] if len(self.datas) > 1 else None

        # Optional intermediate/high-resolution feeds
        try:
            self.data_1h = self.getdatabyname("1h")   # resampled when base=15m
        except KeyError:
            self.data_1h = None
        try:
            self.data_15m = self.getdatabyname("15m")
        except KeyError:
            self.data_15m = None
        try:
            self.data_5m = self.getdatabyname("5m")
        except KeyError:
            self.data_5m = None
        try:
            self.data_2m = self.getdatabyname("2m")
        except KeyError:
            self.data_2m = None
        try:
            self.data_1m = self.getdatabyname("1m")
        except KeyError:
            self.data_1m = None

        # FVG trackers — base, 4H, and optional 15m / 5m / 2m / 1m
        self.fvg_tracker = FVGTracker(
            dubious_break_pct=FVG_DUBIOUS_BREAK_PCT,
            dubious_wait_bars=FVG_DUBIOUS_WAIT_BARS,
        )
        self.fvg_tracker_4h = FVGTracker(
            dubious_break_pct=FVG_DUBIOUS_BREAK_PCT,
            dubious_wait_bars=FVG_DUBIOUS_WAIT_BARS,
        )
        self.fvg_tracker_15m = FVGTracker(
            dubious_break_pct=FVG_DUBIOUS_BREAK_PCT,
            dubious_wait_bars=FVG_DUBIOUS_WAIT_BARS,
        )
        self.fvg_tracker_5m = FVGTracker(
            dubious_break_pct=FVG_DUBIOUS_BREAK_PCT,
            dubious_wait_bars=FVG_DUBIOUS_WAIT_BARS,
        )
        self.fvg_tracker_2m = FVGTracker(
            dubious_break_pct=FVG_DUBIOUS_BREAK_PCT,
            dubious_wait_bars=FVG_DUBIOUS_WAIT_BARS,
        )
        self.fvg_tracker_1m = FVGTracker(
            dubious_break_pct=FVG_DUBIOUS_BREAK_PCT,
            dubious_wait_bars=FVG_DUBIOUS_WAIT_BARS,
        )
        self.liquidity_tracker = LiquidityTracker()

        # Build TF list for structure engine based on available feeds
        tf_list = ["4h", "base"]
        if self.data_1h is not None:
            tf_list.append("1h")
        if self.data_15m is not None:
            tf_list.append("15m")
        if self.data_5m is not None:
            tf_list.append("5m")
        if self.data_2m is not None:
            tf_list.append("2m")
        if self.data_1m is not None:
            tf_list.append("1m")

        # Multi-TF modules
        self.structure_engine = StructureEngine(tf_list)
        self.liq_map = LiquidityMap()
        self.scorer = SetupScorer(
            structure_engine=self.structure_engine,
            liq_map=self.liq_map,
            fvg_high=self.fvg_tracker_4h,
            fvg_base=self.fvg_tracker,
            fvg_15m=self.fvg_tracker_15m,
            fvg_5m=self.fvg_tracker_5m,
        )

        # Risk managers — use trader's chosen contracts ceiling and loss limit
        self.position_sizer = PositionSizer(
            initial_equity=self.p.initial_capital,
            max_contracts=self.p.default_contracts,
            max_loss_per_trade=self.p.max_loss_per_trade,
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
        self._last_1h_len: int = 0
        self._last_15m_len: int = 0
        self._last_5m_len: int = 0
        self._5m_fvg_entries_used: set = set()  # FVG timestamps used for 5m PDF entries
        self._1m_fvg_entries_used: set = set()  # FVG timestamps used for 1m PDF entries
        self._last_2m_len: int = 0
        self._last_1m_len: int = 0
        # SMT (Smart Money Trap) levels detected on 2m bars.
        # Each entry: {"price": float, "direction": "bullish"|"bearish",
        #              "timestamp": pd.Timestamp, "broken": bool}
        self._smt_2m_levels: List[Dict] = []
        self._max_favorable_pnl: float = 0.0
        self._max_favorable_pct_of_tp: float = 0.0
        self._ny_am_open_set: bool = False
        self._tp_price: Optional[float] = None
        self._sl_price: Optional[float] = None
        self._entry_price: Optional[float] = None
        self._entry_time: Optional[datetime] = None
        self._entry_contracts: int = 0
        self._exit_reason: str = ""
        self._bar_count: int = 0
        self._trades_log: List[Dict] = []
        self._pending_order = None
        self._actual_exit_price: Optional[float] = None
        self._recent_swing_high: Optional[float] = None
        self._recent_swing_low: Optional[float] = None

        # Cumulative P&L tracking for total account loss limit
        self._total_pnl: float = 0.0
        self._account_blown: bool = False
        # Stores the bar time when forced-close was ordered (vs when exit fills)
        self._forced_close_time: Optional[datetime] = None
        # True while a close() order is in flight — prevents duplicate forced closes
        self._close_pending: bool = False

        # Trade context snapshot (captured at _execute_entry, stored until notify_trade)
        self._entry_context: Optional[Dict] = None

        # Phase 6.2 — cooldown after a losing trade
        self._cooldown_until_bar: int = 0

        # Phase 6.2 — thesis snapshot at entry (for live re-evaluation logs)
        self._thesis: Optional[Dict] = None

        # Phase 7.3 — manipulation burst cooldown (real-time, not bar-count based)
        self._manipulation_until_ts: Optional[datetime] = None

        # Phase 6.1 — last "map snapshot" used to detect material changes bar-over-bar
        self._last_map_snapshot: Optional[Dict] = None

        # Phase 6.4 — last 5m leading direction, used to suppress redundant logs
        self._last_5m_lead: Optional[str] = None

        # Rejection counters — tallied each bar; printed in stop() for diagnosis
        self._rejection_counts: Dict[str, int] = {
            "no_killzone":              0,
            "cooldown_loss":            0,
            "cooldown_manipulation":    0,
            "kill_switch":              0,
            "gates_long":               0,  # scorer gates failed (LONG)
            "gates_short":              0,  # scorer gates failed (SHORT)
            "score_below_threshold":    0,
            "entry_no_prot_fvg":        0,  # protective_fvg is None at execute
            "entry_no_target":          0,  # target_level is None at execute
            "entry_sl_limit":           0,  # SL × point_value > max_loss_per_trade
            "entry_preflight":          0,  # preflight_check failed
            "no_contracts":             0,
        }

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

        broken_bullish = sum(1 for f in self.fvg_tracker.broken_fvgs
                             if f.fvg_type == FVGType.BULLISH)
        broken_bearish = sum(1 for f in self.fvg_tracker.broken_fvgs
                             if f.fvg_type == FVGType.BEARISH)

        macro_bias = self.structure_engine.get_macro_bias()
        self.log(
            f"CONTEXT: 4H={trend_4h.value} | engine_macro={macro_bias.value} | "
            f"Bull FVG broken={broken_bullish} | Bear FVG broken={broken_bearish} | "
            f"Upside_exhaust={self.liq_map.upside_exhaustion():.1f}/10 "
            f"Downside_exhaust={self.liq_map.downside_exhaustion():.1f}/10"
        )

        # Phase 6.3 — rolling trade pace
        self._log_trade_pace()

    def _maybe_log_5m_scoring(self):
        """
        Phase 6.4 — granular re-score on each new 5m close during NY AM.

        Skips logging unless something changed vs the last 5m bar:
          - Leading direction flipped (long ↔ short)
          - Either side crossed the per-trade threshold for the first time
        Never emits while in a position (already covered by REVIEW logs).
        """
        if not self.p.verbose_5m:
            return
        if self.position:
            return
        if self._get_current_session() != "ny_am":
            return
        if self.data_5m is None:
            return

        price = self.data_5m.close[0]
        self.scorer.set_bar(self._bar_count)
        long_bd, short_bd = self.scorer.score_both(price)

        threshold = SCORER_MIN_SCORE_TRADE_2 if self.kill_switch.trades_today >= 1 else SCORER_MIN_SCORE_TRADE_1
        lead = "long" if long_bd.total_score > short_bd.total_score else "short"
        crossed = (
            (long_bd.gates_passed and long_bd.total_score >= threshold)
            or (short_bd.gates_passed and short_bd.total_score >= threshold)
        )

        if lead != self._last_5m_lead or crossed:
            self.log(
                f"5M @ {price:.1f} → lead={lead.upper()} "
                f"(L={long_bd.total_score:.1f} S={short_bd.total_score:.1f}, "
                f"need ≥{threshold:.0f})",
                "5M",
            )
            self._last_5m_lead = lead

    def _log_trade_pace(self):
        """
        Logs trade count over last 7d / 30d. Emits a ⚠ warning when fewer
        than pace_warn_threshold_7d trades have closed in the last 7 days.
        """
        if not self._trades_log:
            return
        now = self.data_base.datetime.datetime(0)
        last7  = sum(1 for t in self._trades_log
                     if (now - t["timestamp"]).days <= 7)
        last30 = sum(1 for t in self._trades_log
                     if (now - t["timestamp"]).days <= 30)
        warn = last7 < self.p.pace_warn_threshold_7d
        prefix = "⚠ TRADE PACE LOW" if warn else "TRADE PACE"
        self.log(
            f"{prefix}: {last7}/7d, {last30}/30d "
            f"(target ≥{self.p.pace_warn_threshold_7d}/7d)",
            "PACE",
        )

    # =========================================================================
    # PHASE 6.1 — Live "map" snapshot & change detection
    # =========================================================================
    def _capture_map_snapshot(self) -> Dict:
        """Cheap snapshot of the state that defines the trading map."""
        def fvg_counts(tracker):
            if tracker is None:
                return (0, 0, 0, 0)  # bull_active, bear_active, bull_broken, bear_broken
            ba  = sum(1 for f in tracker._active_fvgs if f.fvg_type == FVGType.BULLISH)
            bra = sum(1 for f in tracker._active_fvgs if f.fvg_type == FVGType.BEARISH)
            bb  = sum(1 for f in tracker._broken_fvgs if f.fvg_type == FVGType.BULLISH)
            brb = sum(1 for f in tracker._broken_fvgs if f.fvg_type == FVGType.BEARISH)
            return (ba, bra, bb, brb)

        macro = self.structure_engine.get_macro_bias()
        base_bias = self.structure_engine.get_bias("base")

        return {
            "macro":        macro,
            "base_bias":    base_bias,
            "fvg_4h":       fvg_counts(self.fvg_tracker_4h),
            "fvg_1h":       fvg_counts(self.fvg_tracker),       # base = 1H
            "fvg_15m":      fvg_counts(self.fvg_tracker_15m),
            "fvg_5m":       fvg_counts(self.fvg_tracker_5m),
            "fvg_2m":       fvg_counts(self.fvg_tracker_2m),
            "fvg_1m":       fvg_counts(self.fvg_tracker_1m),
            "ath":          self.liq_map.ath,
            "near_ath":     self.liq_map.is_near_ath(),
            "post_rev":     self.liq_map.is_post_ath_reversal(),
            "n_sweeps":     len(self.liq_map.sweep_history),
        }

    def _emit_map_update_if_changed(self):
        """
        Emits a MAP UPDATE log only when something material changed since the
        last snapshot — avoids per-bar noise.
        """
        snap = self._capture_map_snapshot()
        prev = self._last_map_snapshot
        self._last_map_snapshot = snap
        if prev is None:
            return

        changes = []
        if snap["macro"] != prev["macro"]:
            changes.append(f"macro {prev['macro'].value}→{snap['macro'].value}")
        if snap["base_bias"] != prev["base_bias"]:
            changes.append(f"1H bias {prev['base_bias'].value}→{snap['base_bias'].value}")

        # FVG breaks (broken count went up at any TF)
        for tf, key in (("4h", "fvg_4h"), ("1h", "fvg_1h"),
                        ("15m", "fvg_15m"), ("5m", "fvg_5m")):
            ba_p, bra_p, bb_p, brb_p = prev[key]
            ba,   bra,   bb,   brb   = snap[key]
            if bb > bb_p:
                changes.append(f"{tf}: +{bb - bb_p} bull FVG broken")
            if brb > brb_p:
                changes.append(f"{tf}: +{brb - brb_p} bear FVG broken")

        if snap["n_sweeps"] > prev["n_sweeps"]:
            changes.append(f"+{snap['n_sweeps'] - prev['n_sweeps']} new sweep(s)")
        if snap["near_ath"] != prev["near_ath"]:
            changes.append(f"near_ATH={snap['near_ath']}")
        if snap["post_rev"] != prev["post_rev"]:
            changes.append(f"post_ATH_reversal={snap['post_rev']}")

        if changes:
            self.log("MAP UPDATE: " + " | ".join(changes), "MAP")

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

            # Phase 8.2 — keep scorer's swing range in sync
            self.liq_map.set_swing_range(self._recent_swing_high, self._recent_swing_low)

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
            # Phase 8.1 — feed rolling ATL from every new 4H bar
            self.liq_map.update_atl(
                self.data_4h.low[0],
                pd.Timestamp(self.data_4h.datetime.datetime(0)),
            )

        # ── 1h bars (resampled from 15m base, when base_tf="15m") ────────────
        if self.data_1h is not None and len(self.data_1h) > self._last_1h_len:
            self._last_1h_len = len(self.data_1h)
            self.structure_engine.update(
                "1h",
                self.data_1h.open[0], self.data_1h.high[0],
                self.data_1h.low[0],  self.data_1h.close[0],
                pd.Timestamp(self.data_1h.datetime.datetime(0)),
            )

        # ── 15m bars ──────────────────────────────────────────────────────────
        if self.data_15m is not None:
            new_15m = len(self.data_15m) - self._last_15m_len
            if new_15m > 0 and len(self.data_15m) >= 3:
                # Feed structure engine for all new 15m bars (oldest → newest)
                for offset in range(new_15m - 1, -1, -1):
                    self.structure_engine.update(
                        "15m",
                        self.data_15m.open[-offset],
                        self.data_15m.high[-offset],
                        self.data_15m.low[-offset],
                        self.data_15m.close[-offset],
                        pd.Timestamp(self.data_15m.datetime.datetime(-offset)),
                    )
                # FVG detection on most recent 3 bars of 15m
                h2_15 = self.data_15m.high[-2]
                h0_15 = self.data_15m.high[0]
                l2_15 = self.data_15m.low[-2]
                l0_15 = self.data_15m.low[0]
                ts_15 = pd.Timestamp(self.data_15m.datetime.datetime(0))
                bar_15 = self._last_15m_len + new_15m
                if h2_15 < l0_15:
                    self.fvg_tracker_15m.add_fvgs([FairValueGap(
                        fvg_type=FVGType.BULLISH, top=l0_15, bottom=h2_15,
                        timestamp=ts_15, timeframe="15m", candle_idx=bar_15,
                    )])
                if l2_15 > h0_15:
                    self.fvg_tracker_15m.add_fvgs([FairValueGap(
                        fvg_type=FVGType.BEARISH, top=l2_15, bottom=h0_15,
                        timestamp=ts_15, timeframe="15m", candle_idx=bar_15,
                    )])
                self.fvg_tracker_15m.update(
                    self.data_15m.high[0], self.data_15m.low[0], self.data_15m.close[0]
                )
                self._last_15m_len += new_15m

        # ── 5m bars ───────────────────────────────────────────────────────────
        if self.data_5m is not None:
            new_5m = len(self.data_5m) - self._last_5m_len
            if new_5m > 0 and len(self.data_5m) >= 3:
                for offset in range(new_5m - 1, -1, -1):
                    self.structure_engine.update(
                        "5m",
                        self.data_5m.open[-offset],
                        self.data_5m.high[-offset],
                        self.data_5m.low[-offset],
                        self.data_5m.close[-offset],
                        pd.Timestamp(self.data_5m.datetime.datetime(-offset)),
                    )
                h2_5 = self.data_5m.high[-2]
                h0_5 = self.data_5m.high[0]
                l2_5 = self.data_5m.low[-2]
                l0_5 = self.data_5m.low[0]
                ts_5 = pd.Timestamp(self.data_5m.datetime.datetime(0))
                bar_5 = self._last_5m_len + new_5m
                if h2_5 < l0_5:
                    self.fvg_tracker_5m.add_fvgs([FairValueGap(
                        fvg_type=FVGType.BULLISH, top=l0_5, bottom=h2_5,
                        timestamp=ts_5, timeframe="5m", candle_idx=bar_5,
                    )])
                if l2_5 > h0_5:
                    self.fvg_tracker_5m.add_fvgs([FairValueGap(
                        fvg_type=FVGType.BEARISH, top=l2_5, bottom=h0_5,
                        timestamp=ts_5, timeframe="5m", candle_idx=bar_5,
                    )])

                # Snapshot active FVGs before update (for broken-FVG detection)
                _pre_5m_bear = {f.timestamp for f in self.fvg_tracker_5m._active_fvgs if f.fvg_type == FVGType.BEARISH}
                _pre_5m_bull = {f.timestamp for f in self.fvg_tracker_5m._active_fvgs if f.fvg_type == FVGType.BULLISH}

                self.fvg_tracker_5m.update(
                    self.data_5m.high[0], self.data_5m.low[0], self.data_5m.close[0]
                )
                self._last_5m_len += new_5m

                # Phase 6.4 — granular intra-bar scoring on each new 5m close
                self._maybe_log_5m_scoring()

                # PDF trigger on 5m bars — always active (not just when 1m is absent)
                # 1m trigger is higher-precision; position/pending checks prevent double entry.
                if not self.position and self._pending_order is None:
                    _post_5m_bear = {f.timestamp for f in self.fvg_tracker_5m._active_fvgs if f.fvg_type == FVGType.BEARISH}
                    _post_5m_bull = {f.timestamp for f in self.fvg_tracker_5m._active_fvgs if f.fvg_type == FVGType.BULLISH}
                    _new_bear_broken = _pre_5m_bear - _post_5m_bear
                    _new_bull_broken = _pre_5m_bull - _post_5m_bull
                    if _new_bear_broken or _new_bull_broken:
                        self._check_entry_pdf_trigger(
                            trigger_close=self.data_5m.close[0],
                            trigger_open=self.data_5m.open[0],
                            trigger_dt=self.data_5m.datetime.datetime(0),
                            trigger_tf="5m",
                            newly_broken_bear=_new_bear_broken,
                            newly_broken_bull=_new_bull_broken,
                            trigger_tracker=self.fvg_tracker_5m,
                            entries_used=self._5m_fvg_entries_used,
                        )

        # ── 2m bars ───────────────────────────────────────────────────────────
        if self.data_2m is not None:
            new_2m = len(self.data_2m) - self._last_2m_len
            if new_2m > 0 and len(self.data_2m) >= 3:
                h2_2 = self.data_2m.high[-2]
                h0_2 = self.data_2m.high[0]
                l2_2 = self.data_2m.low[-2]
                l0_2 = self.data_2m.low[0]
                c0_2 = self.data_2m.close[0]
                ts_2 = pd.Timestamp(self.data_2m.datetime.datetime(0))
                bar_2 = self._last_2m_len + new_2m
                if h2_2 < l0_2:
                    self.fvg_tracker_2m.add_fvgs([FairValueGap(
                        fvg_type=FVGType.BULLISH, top=l0_2, bottom=h2_2,
                        timestamp=ts_2, timeframe="2m", candle_idx=bar_2,
                    )])
                if l2_2 > h0_2:
                    self.fvg_tracker_2m.add_fvgs([FairValueGap(
                        fvg_type=FVGType.BEARISH, top=l2_2, bottom=h0_2,
                        timestamp=ts_2, timeframe="2m", candle_idx=bar_2,
                    )])
                self.fvg_tracker_2m.update(h0_2, l0_2, c0_2)
                self._last_2m_len += new_2m

                # ── SMT detection on 2m bars ──────────────────────────────────
                # A bullish SMT forms when the current 2m bar's low is within
                # SMT_TOL pts of a previous 2m bar's low (last 30 bars) AND
                # both bars CLOSED above that low → price failed twice to break down.
                # A bearish SMT mirrors this with highs.
                # Invalidate existing SMTs when price closes through them.
                SMT_TOL = 5.0    # pts — how close the two lows/highs must be
                SMT_LOOKBACK = min(30, len(self.data_2m) - 1)

                # Invalidate broken SMT levels
                for smt in self._smt_2m_levels:
                    if smt["broken"]:
                        continue
                    if smt["direction"] == "bullish" and c0_2 < smt["price"] - SMT_TOL:
                        smt["broken"] = True
                    elif smt["direction"] == "bearish" and c0_2 > smt["price"] + SMT_TOL:
                        smt["broken"] = True

                # Detect new bullish SMT: current low ≈ a recent low, close above both
                if c0_2 > l0_2 + 1.0:  # current bar closed above its own low
                    for i in range(1, SMT_LOOKBACK):
                        prev_low  = self.data_2m.low[-i]
                        prev_close = self.data_2m.close[-i]
                        if abs(l0_2 - prev_low) <= SMT_TOL and prev_close > prev_low + 1.0:
                            smt_price = (l0_2 + prev_low) / 2.0
                            # Only register if not already tracked near this level
                            already = any(
                                s["direction"] == "bullish"
                                and abs(s["price"] - smt_price) <= SMT_TOL * 2
                                and not s["broken"]
                                for s in self._smt_2m_levels
                            )
                            if not already:
                                self._smt_2m_levels.append({
                                    "price":     smt_price,
                                    "direction": "bullish",
                                    "timestamp": ts_2,
                                    "broken":    False,
                                })
                                self.log(
                                    f"SMT BULLISH 2m @ {smt_price:.0f} "
                                    f"(lows: {prev_low:.0f} bar-{i} ↔ {l0_2:.0f} now)",
                                    "SMT",
                                )
                            break

                # Detect new bearish SMT: current high ≈ a recent high, close below both
                if c0_2 < h0_2 - 1.0:
                    for i in range(1, SMT_LOOKBACK):
                        prev_high  = self.data_2m.high[-i]
                        prev_close = self.data_2m.close[-i]
                        if abs(h0_2 - prev_high) <= SMT_TOL and prev_close < prev_high - 1.0:
                            smt_price = (h0_2 + prev_high) / 2.0
                            already = any(
                                s["direction"] == "bearish"
                                and abs(s["price"] - smt_price) <= SMT_TOL * 2
                                and not s["broken"]
                                for s in self._smt_2m_levels
                            )
                            if not already:
                                self._smt_2m_levels.append({
                                    "price":     smt_price,
                                    "direction": "bearish",
                                    "timestamp": ts_2,
                                    "broken":    False,
                                })
                                self.log(
                                    f"SMT BEARISH 2m @ {smt_price:.0f} "
                                    f"(highs: {prev_high:.0f} bar-{i} ↔ {h0_2:.0f} now)",
                                    "SMT",
                                )
                            break

                # Prune stale SMTs (older than 60 bars of 2m ≈ 2 hours)
                self._smt_2m_levels = [
                    s for s in self._smt_2m_levels
                    if not s["broken"]
                    and (ts_2 - s["timestamp"]).total_seconds() <= 7200
                ]

        # ── 1m bars ───────────────────────────────────────────────────────────
        if self.data_1m is not None:
            new_1m = len(self.data_1m) - self._last_1m_len
            if new_1m > 0 and len(self.data_1m) >= 3:
                h2_1 = self.data_1m.high[-2]
                h0_1 = self.data_1m.high[0]
                l2_1 = self.data_1m.low[-2]
                l0_1 = self.data_1m.low[0]
                ts_1 = pd.Timestamp(self.data_1m.datetime.datetime(0))
                bar_1 = self._last_1m_len + new_1m

                # Snapshot before update to detect newly broken FVGs this bar
                _pre_1m_bear = {f.timestamp for f in self.fvg_tracker_1m._active_fvgs if f.fvg_type == FVGType.BEARISH}
                _pre_1m_bull = {f.timestamp for f in self.fvg_tracker_1m._active_fvgs if f.fvg_type == FVGType.BULLISH}

                if h2_1 < l0_1:
                    self.fvg_tracker_1m.add_fvgs([FairValueGap(
                        fvg_type=FVGType.BULLISH, top=l0_1, bottom=h2_1,
                        timestamp=ts_1, timeframe="1m", candle_idx=bar_1,
                    )])
                if l2_1 > h0_1:
                    self.fvg_tracker_1m.add_fvgs([FairValueGap(
                        fvg_type=FVGType.BEARISH, top=l2_1, bottom=h0_1,
                        timestamp=ts_1, timeframe="1m", candle_idx=bar_1,
                    )])
                self.fvg_tracker_1m.update(
                    self.data_1m.high[0], self.data_1m.low[0], self.data_1m.close[0]
                )
                self._last_1m_len += new_1m

                if not self.position and self._pending_order is None:
                    _post_1m_bear = {f.timestamp for f in self.fvg_tracker_1m._active_fvgs if f.fvg_type == FVGType.BEARISH}
                    _post_1m_bull = {f.timestamp for f in self.fvg_tracker_1m._active_fvgs if f.fvg_type == FVGType.BULLISH}
                    _new_1m_bear_broken = _pre_1m_bear - _post_1m_bear
                    _new_1m_bull_broken = _pre_1m_bull - _post_1m_bull
                    if _new_1m_bear_broken or _new_1m_bull_broken:
                        self._check_entry_pdf_trigger(
                            trigger_close=self.data_1m.close[0],
                            trigger_open=self.data_1m.open[0],
                            trigger_dt=self.data_1m.datetime.datetime(0),
                            trigger_tf="1m",
                            newly_broken_bear=_new_1m_bear_broken,
                            newly_broken_bull=_new_1m_bull_broken,
                            trigger_tracker=self.fvg_tracker_1m,
                            entries_used=self._1m_fvg_entries_used,
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
                self._5m_fvg_entries_used.clear()
                self._1m_fvg_entries_used.clear()

    # =========================================================================
    # ENTRY LOGIC — Buscar oportunidades
    # =========================================================================
    # =========================================================================
    # SESSION / KILLZONE HELPERS
    # =========================================================================
    def _session_for_dt(self, dt) -> Optional[str]:
        """Return the KILLZONES key for a given datetime, or None."""
        current_time = dt.time()
        for key, zone in KILLZONES.items():
            sh, sm = map(int, zone.start_et.split(":"))
            eh, em = map(int, zone.end_et.split(":"))
            zone_start = dtime(sh, sm)
            zone_end = dtime(eh, em)
            if zone_start < zone_end:
                if zone_start <= current_time < zone_end:
                    return key
                continue
            if current_time >= zone_start or current_time < zone_end:
                return key
        return None

    def _get_current_session(self) -> Optional[str]:
        """Return the KILLZONES key for the current base-TF bar, or None."""
        return self._session_for_dt(self.data_base.datetime.datetime(0))

    # =========================================================================
    # PHASE 7.3 — Manipulation burst detection
    # =========================================================================
    def _update_manipulation_state(self):
        """
        Detects when ≥3 sweep events occurred within the last 60 minutes and
        arms a 15-minute real-time cooldown. Re-arms whenever a new burst is
        detected before the previous cooldown expires (extends the window).

        Called every bar in next(). Only logs when the cooldown is first set
        or extended — not on every bar of the cooldown period.
        """
        if len(self.liq_map.sweep_history) < 3:
            return

        now_ts = pd.Timestamp(self.data_base.datetime.datetime(0))
        window_start = now_ts - pd.Timedelta(minutes=60)

        recent = [
            sw for sw in self.liq_map.sweep_history
            if sw.timestamp >= window_start
        ]

        if len(recent) < 3:
            return

        last_sweep_ts = max(sw.timestamp for sw in recent)
        new_until = (last_sweep_ts + pd.Timedelta(minutes=15)).to_pydatetime()

        # Only update (and log) if this extends or creates the cooldown
        if self._manipulation_until_ts is None or new_until > self._manipulation_until_ts:
            self._manipulation_until_ts = new_until
            self.log(
                f"MANIPULATION DETECTED: {len(recent)} sweeps in last 60m. "
                f"No new entries until {self._manipulation_until_ts.strftime('%H:%M')}",
                "WARN",
            )

    # =========================================================================
    # ENTRY LOGIC — Scorer-based, evaluates BOTH sides every bar
    # =========================================================================
    def _check_entry(self):
        """
        Evalúa long Y short cada barra usando el SetupScorer.
        No hay lock de dirección — el scorer decide basándose en
        la suma de ingredientes ICT (sweep + CHoCH + FVG path + targets).
        """
        if self._account_blown:
            return

        if self.position:
            return

        if self._pending_order is not None:
            return

        # Solo durante NY AM y NY PM killzones
        if self._get_current_session() not in ("ny_am", "ny_pm"):
            self._rejection_counts["no_killzone"] += 1
            return

        # Phase 6.2 — cooldown after a losing trade (prevents over-reactive flips)
        if self._bar_count < self._cooldown_until_bar:
            remaining = self._cooldown_until_bar - self._bar_count
            self.log(
                f"COOLDOWN: {remaining} bar(s) remaining after recent loss",
                "SKIP",
            )
            self._rejection_counts["cooldown_loss"] += 1
            return

        # Phase 7.3 — manipulation burst cooldown (real-time, 15 minutes)
        if self._manipulation_until_ts is not None:
            now = self.data_base.datetime.datetime(0)
            if now < self._manipulation_until_ts:
                remaining_m = int((self._manipulation_until_ts - now).total_seconds() / 60)
                self.log(
                    f"MANIPULATION COOLDOWN: {remaining_m}m remaining "
                    f"(until {self._manipulation_until_ts.strftime('%H:%M')})",
                    "SKIP",
                )
                self._rejection_counts["cooldown_manipulation"] += 1
                return
            else:
                self._manipulation_until_ts = None  # expired

        can_trade, _ = self.kill_switch.can_open_trade()
        if not can_trade:
            self._rejection_counts["kill_switch"] += 1
            return

        price = self.data_base.close[0]
        self.scorer.set_bar(self._bar_count)
        threshold = SCORER_MIN_SCORE_TRADE_2 if self.kill_switch.trades_today >= 1 else SCORER_MIN_SCORE_TRADE_1
        long_bd, short_bd = self.scorer.score_both(price)

        # Log both sides each bar so we can see what the scorer sees
        self.log(f"SCORE {long_bd.log_str()}", "SCORE")
        self.log(f"SCORE {short_bd.log_str()}", "SCORE")

        setup = self.scorer.best_setup(price, self.kill_switch.trades_today)

        if setup is not None:
            self._execute_entry(setup, price)
        else:
            # Tally per-direction gate failures for diagnosis
            for bd in (long_bd, short_bd):
                key = f"gates_{bd.direction}"
                if not bd.gates_passed:
                    self._rejection_counts[key] += 1
                elif bd.total_score < threshold:
                    self._rejection_counts["score_below_threshold"] += 1
                reason = bd.rejection_reason()
                if reason:
                    self.log(
                        f"  SKIP {bd.direction.upper()}: {reason} "
                        f"(score={bd.total_score:.1f} need={threshold:.0f})",
                        "SKIP",
                    )

    # =========================================================================
    # PDF ENTRY TRIGGER — Rompimiento de FVG opuesto dentro de FVG container
    # =========================================================================
    def _find_container_fvg(
        self, direction: str, trigger_fvg: "FairValueGap", price: float
    ) -> "Optional[FairValueGap]":
        """
        Find the first active FVG from a higher TF that contains both the
        trigger FVG range and the current price.

        For LONG:  look for Bullish FVGs in (base/1h → 15m → 5m) order.
        For SHORT: look for Bearish FVGs in the same order.

        'Contains' = container.bottom ≤ trigger.bottom  AND
                     container.top    ≥ trigger.top      (±TOLERANCE)
        Price must also be inside or very close to the container.
        """
        TOL = 10.0  # pts — boundary tolerance

        trackers = [
            (self.fvg_tracker, "base"),
            (self.fvg_tracker_15m, "15m"),
            (self.fvg_tracker_5m, "5m"),
        ]

        if direction == "bullish":
            for tracker, _ in trackers:
                if tracker is None:
                    continue
                for fvg in tracker.active_bullish:
                    # Price is inside (or very close to) a higher-TF bullish FVG
                    if fvg.bottom - TOL <= price <= fvg.top + TOL * 3:
                        return fvg
        else:
            for tracker, _ in trackers:
                if tracker is None:
                    continue
                for fvg in tracker.active_bearish:
                    # Price is inside (or very close to) a higher-TF bearish FVG
                    if fvg.bottom - TOL * 3 <= price <= fvg.top + TOL:
                        return fvg
        return None

    def _find_protective_fvg(
        self,
        direction: str,
        price: float,
        trigger_tracker: "FVGTracker",
    ) -> "Optional[FairValueGap]":
        """
        Find the most recent active FVG (in trigger TF first, then 5m/15m fallback)
        to anchor the SL.

        LONG:  most recent Bullish FVG below price (within 150 pts)
        SHORT: most recent Bearish FVG above price (within 150 pts)
        """
        MAX_DIST = 150.0

        if direction == "long":
            for tracker in [trigger_tracker, self.fvg_tracker_5m,
                            self.fvg_tracker_15m, self.fvg_tracker]:
                if tracker is None:
                    continue
                cands = [f for f in tracker.active_bullish
                         if f.top <= price and price - f.top <= MAX_DIST]
                if cands:
                    return max(cands, key=lambda f: f.candle_idx)
        else:
            for tracker in [trigger_tracker, self.fvg_tracker_5m,
                            self.fvg_tracker_15m, self.fvg_tracker]:
                if tracker is None:
                    continue
                cands = [f for f in tracker.active_bearish
                         if f.bottom >= price and f.bottom - price <= MAX_DIST]
                if cands:
                    return min(cands, key=lambda f: f.bottom - price)
        return None

    def _find_tp_unmitigated(
        self, direction: str, price: float
    ) -> "tuple[Optional[float], str]":
        """
        Find the nearest unmitigated (active) opposing FVG to use as TP.

        LONG:  nearest active Bearish FVG above price → TP = fvg.top
        SHORT: nearest active Bullish FVG below price → TP = fvg.bottom

        Returns (tp_price, label) or (None, '') if nothing found.
        """
        MIN_DIST = 15.0
        MAX_DIST = 500.0

        if direction == "long":
            for tracker, tf in [
                (self.fvg_tracker_5m,  "5m"),
                (self.fvg_tracker_15m, "15m"),
                (self.fvg_tracker,     "base"),
                (self.fvg_tracker_4h,  "4h"),
            ]:
                if tracker is None:
                    continue
                cands = [f for f in tracker.active_bearish
                         if MIN_DIST < f.bottom - price <= MAX_DIST]
                if cands:
                    best = min(cands, key=lambda f: f.bottom)
                    return best.top, f"Bear FVG {tf} ({best.bottom:.0f}–{best.top:.0f})"
        else:
            for tracker, tf in [
                (self.fvg_tracker_5m,  "5m"),
                (self.fvg_tracker_15m, "15m"),
                (self.fvg_tracker,     "base"),
                (self.fvg_tracker_4h,  "4h"),
            ]:
                if tracker is None:
                    continue
                cands = [f for f in tracker.active_bullish
                         if MIN_DIST < price - f.top <= MAX_DIST]
                if cands:
                    best = max(cands, key=lambda f: f.top)
                    return best.bottom, f"Bull FVG {tf} ({best.bottom:.0f}–{best.top:.0f})"
        return None, ""

    def _find_smt_in_container(
        self, direction: str, container: "FairValueGap"
    ) -> "Optional[Dict]":
        """
        Return the most recent valid 2m SMT level whose price falls inside
        the container FVG, or None.

        direction = "bullish" → look for a bullish SMT (two held lows)
                                that supports a LONG entry inside the container
        direction = "bearish" → bearish SMT (two held highs) for SHORT
        """
        TOL = 10.0
        candidates = [
            s for s in self._smt_2m_levels
            if not s["broken"]
            and s["direction"] == direction
            and container.bottom - TOL <= s["price"] <= container.top + TOL
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s["timestamp"])

    def _check_entry_pdf_trigger(
        self,
        trigger_close: float,
        trigger_open: float,
        trigger_dt: "datetime",
        trigger_tf: str,
        newly_broken_bear: set,
        newly_broken_bull: set,
        trigger_tracker: "FVGTracker",
        entries_used: set,
    ):
        """
        PDF-style entry: fires when a micro-TF FVG of OPPOSING direction
        breaks (close crosses its boundary) INSIDE a same-direction container FVG.

        LONG:  newly broken Bearish FVG (micro TF) inside a Bullish container
        SHORT: newly broken Bullish FVG (micro TF) inside a Bearish container

        SL  = protective FVG bottom/top ± 5 pts buffer
        TP  = nearest unmitigated opposing FVG; fallback to liquidity levels

        CISD bonus (+1.0): the breaking candle opened on the wrong side of the FVG
        boundary (Change in State of Delivery), confirming a shift in price delivery.
        """
        if self._account_blown:
            return
        if self.position or self._pending_order is not None:
            return
        if self._session_for_dt(trigger_dt) not in ("ny_am", "ny_pm"):
            return

        # Use base bar time (same reference as _should_force_close) to avoid
        # timezone mismatch between 1m trigger_dt and ET-based force-close cutoff.
        # 30-minute buffer ensures the trade has runway for SL/TP to be hit.
        _base_dt = self.data_base.datetime.datetime(0)
        _force_close_et = self._get_vet_close_in_et(_base_dt)
        _cutoff_min = _force_close_et.hour * 60 + _force_close_et.minute - 30
        if _base_dt.time() >= dtime(_cutoff_min // 60, _cutoff_min % 60):
            return

        if self._bar_count < self._cooldown_until_bar:
            return
        if self._manipulation_until_ts is not None:
            if trigger_dt < self._manipulation_until_ts:
                return
            self._manipulation_until_ts = None

        can_trade, _ = self.kill_switch.can_open_trade()
        if not can_trade:
            return

        SL_BUFFER = 5.0   # pts beyond the protective FVG boundary

        # ── LONG: bearish micro-TF FVG broken → price broke resistance ───────
        for broken_ts in newly_broken_bear:
            if self.position or self._pending_order is not None:
                return
            if broken_ts in entries_used:
                continue
            broken_fvg = next(
                (f for f in trigger_tracker.broken_fvgs
                 if f.fvg_type == FVGType.BEARISH and f.timestamp == broken_ts),
                None,
            )
            if broken_fvg is None:
                continue

            container = self._find_container_fvg("bullish", broken_fvg, trigger_close)
            if container is None:
                continue

            prot_fvg = self._find_protective_fvg("long", trigger_close, trigger_tracker)
            if prot_fvg is None:
                continue

            sl_price = prot_fvg.bottom - SL_BUFFER
            sl_dist  = trigger_close - sl_price
            if sl_dist <= 0 or sl_dist > 150:
                continue

            tp_price, tp_label = self._find_tp_unmitigated("long", trigger_close)
            if tp_price is None:
                for lvl in self.liquidity_tracker.get_nearest_buyside(trigger_close):
                    if lvl.price > trigger_close + 10:
                        tp_price = lvl.price
                        tp_label = getattr(lvl, "label", "Liquidez") or "Liquidez"
                        break
            if tp_price is None:
                tp_price = trigger_close + sl_dist
                tp_label = "1:1 sintético"

            if tp_price - trigger_close <= 0:
                continue

            target_liq = LiquidityLevel(
                level_type=LiquidityType.SWING_HIGH,
                price=tp_price,
                timestamp=pd.Timestamp(trigger_dt),
                label=tp_label,
            )

            # CISD: breaking candle opened below FVG top → Change in State of Delivery
            cisd_long = trigger_open < broken_fvg.top
            cisd_score = 1.0 if cisd_long else 0.0
            cisd_reason = (
                f"CISD bullish: vela abrió {trigger_open:.0f} < FVG top {broken_fvg.top:.0f} → +1.0"
                if cisd_long else ""
            )

            # SMT confirmation: bullish 2m SMT inside the container → +1.5 score
            smt = self._find_smt_in_container("bullish", container)
            smt_score = 1.5 if smt is not None else 0.0
            smt_reason = (
                f"SMT bullish 2m @ {smt['price']:.0f} dentro del container → +1.5"
                if smt is not None else ""
            )

            bd = ScoreBreakdown("long")
            bd.protective_fvg   = prot_fvg
            bd.target_level     = target_liq
            bd.has_choch        = True
            bd.has_protective_fvg = True
            bd.rr_filter_passed = True
            bd.total_score      = 8.0 + cisd_score + smt_score
            bd.reasons = [
                f"PDF gatillo ({trigger_tf}): bear FVG {broken_fvg.bottom:.0f}–"
                f"{broken_fvg.top:.0f} roto @ {trigger_close:.0f}",
                f"Container: {container.timeframe} bull FVG "
                f"{container.bottom:.0f}–{container.top:.0f}",
                f"FVG protector ({prot_fvg.timeframe}): "
                f"{prot_fvg.bottom:.0f}–{prot_fvg.top:.0f}",
                f"TP: {tp_label} @ {tp_price:.0f} | SL={sl_price:.0f} ({sl_dist:.0f}pts)",
            ]
            if cisd_reason:
                bd.reasons.append(cisd_reason)
            if smt_reason:
                bd.reasons.append(smt_reason)

            entries_used.add(broken_ts)
            self._execute_entry(bd, trigger_close)
            if self._entry_time is not None:
                self._entry_time = trigger_dt
            return

        # ── SHORT: bullish micro-TF FVG broken → price broke support ─────────
        for broken_ts in newly_broken_bull:
            if self.position or self._pending_order is not None:
                return
            if broken_ts in entries_used:
                continue
            broken_fvg = next(
                (f for f in trigger_tracker.broken_fvgs
                 if f.fvg_type == FVGType.BULLISH and f.timestamp == broken_ts),
                None,
            )
            if broken_fvg is None:
                continue

            container = self._find_container_fvg("bearish", broken_fvg, trigger_close)
            if container is None:
                continue

            prot_fvg = self._find_protective_fvg("short", trigger_close, trigger_tracker)
            if prot_fvg is None:
                continue

            sl_price = prot_fvg.top + SL_BUFFER
            sl_dist  = sl_price - trigger_close
            if sl_dist <= 0 or sl_dist > 150:
                continue

            tp_price, tp_label = self._find_tp_unmitigated("short", trigger_close)
            if tp_price is None:
                for lvl in self.liquidity_tracker.get_nearest_sellside(trigger_close):
                    if lvl.price < trigger_close - 10:
                        tp_price = lvl.price
                        tp_label = getattr(lvl, "label", "Liquidez") or "Liquidez"
                        break
            if tp_price is None:
                tp_price = trigger_close - sl_dist
                tp_label = "1:1 sintético"

            if trigger_close - tp_price <= 0:
                continue

            target_liq = LiquidityLevel(
                level_type=LiquidityType.SWING_LOW,
                price=tp_price,
                timestamp=pd.Timestamp(trigger_dt),
                label=tp_label,
            )

            # CISD: breaking candle opened above FVG bottom → Change in State of Delivery
            cisd_short = trigger_open > broken_fvg.bottom
            cisd_score = 1.0 if cisd_short else 0.0
            cisd_reason = (
                f"CISD bearish: vela abrió {trigger_open:.0f} > FVG bottom {broken_fvg.bottom:.0f} → +1.0"
                if cisd_short else ""
            )

            smt = self._find_smt_in_container("bearish", container)
            smt_score = 1.5 if smt is not None else 0.0
            smt_reason = (
                f"SMT bearish 2m @ {smt['price']:.0f} dentro del container → +1.5"
                if smt is not None else ""
            )

            bd = ScoreBreakdown("short")
            bd.protective_fvg   = prot_fvg
            bd.target_level     = target_liq
            bd.has_choch        = True
            bd.has_protective_fvg = True
            bd.rr_filter_passed = True
            bd.total_score      = 8.0 + cisd_score + smt_score
            bd.reasons = [
                f"PDF gatillo ({trigger_tf}): bull FVG {broken_fvg.bottom:.0f}–"
                f"{broken_fvg.top:.0f} roto @ {trigger_close:.0f}",
                f"Container: {container.timeframe} bear FVG "
                f"{container.bottom:.0f}–{container.top:.0f}",
                f"FVG protector ({prot_fvg.timeframe}): "
                f"{prot_fvg.bottom:.0f}–{prot_fvg.top:.0f}",
                f"TP: {tp_label} @ {tp_price:.0f} | SL={sl_price:.0f} ({sl_dist:.0f}pts)",
            ]
            if cisd_reason:
                bd.reasons.append(cisd_reason)
            if smt_reason:
                bd.reasons.append(smt_reason)

            entries_used.add(broken_ts)
            self._execute_entry(bd, trigger_close)
            if self._entry_time is not None:
                self._entry_time = trigger_dt
            return

    def _pick_protective_fvg(
        self,
        price: float,
        direction: str,
        setup_fvg: Optional[FairValueGap],
    ) -> Optional[FairValueGap]:
        """
        Pick the protective FVG used to manage the trade exit.

        Preference: closest active 1m FVG between price and the setup's
        structural FVG. Falls back to 5m if 1m is unavailable (yfinance
        only serves 1m for the last 7 days).

        For LONG: candidate is bullish, sits below `price`, and its top is
        at or above `setup_fvg.bottom` (so the gap really protects the trade).
        For SHORT: mirrored.
        """
        is_long = direction == "long"
        boundary = (setup_fvg.bottom if (setup_fvg and is_long)
                    else setup_fvg.top if setup_fvg else None)

        for tracker in (self.fvg_tracker_1m, self.fvg_tracker_5m):
            if is_long:
                cands = [
                    f for f in tracker.active_bullish
                    if f.top <= price
                    and (boundary is None or f.top >= boundary)
                ]
                if cands:
                    return max(cands, key=lambda f: f.top)  # closest to price
            else:
                cands = [
                    f for f in tracker.active_bearish
                    if f.bottom >= price
                    and (boundary is None or f.bottom <= boundary)
                ]
                if cands:
                    return min(cands, key=lambda f: f.bottom)

        return setup_fvg  # last resort: keep the setup's FVG

    def _execute_entry(self, setup: ScoreBreakdown, price: float):
        """Ejecuta una entrada basada en el ScoreBreakdown del scorer."""
        if setup.protective_fvg is None or setup.target_level is None:
            missing = []
            if setup.protective_fvg is None:
                missing.append("protective_fvg")
                self._rejection_counts["entry_no_prot_fvg"] += 1
            if setup.target_level is None:
                missing.append("target_level")
                self._rejection_counts["entry_no_target"] += 1
            self.log(f"  ENTRY ABORTED: {', '.join(missing)} is None — setup incomplete", "WARN")
            return

        direction = setup.direction
        tp_price = setup.target_level.price

        # ── Protective FVG must be 1m (fallback 5m if 1m unavailable). ────────
        # The setup's protective FVG (could be 1h/15m/5m) is used only for
        # scoring. The actual *managed* protective FVG is the closest higher-
        # resolution gap between price and the setup's protective FVG.
        protective_fvg = self._pick_protective_fvg(price, direction, setup.protective_fvg)
        if protective_fvg is None:
            self.log(
                "  ENTRY ABORTED: no 1m/5m protective FVG between price and "
                "the setup's protective FVG", "WARN"
            )
            self._rejection_counts["entry_no_prot_fvg"] += 1
            return

        if direction == "long":
            sl_price = protective_fvg.bottom
            tp_points = tp_price - price
        else:
            sl_price = protective_fvg.top
            tp_points = price - tp_price

        # Phase 8.3 — Refine SL: push it just beyond the nearest fresh
        # liquidity level on the far side of the protective FVG.
        # Avoids wick/fake-out stop-outs while keeping the SL anchored to
        # a level where a touch implies genuine structural breakdown.
        _SL_LIQ_BUFFER  = 5.0    # pts beyond the liquidity level
        _SL_SEARCH_DIST = 100.0  # max distance to search for that level

        if direction == "long":
            ssl = [
                l for l in self.liq_map.levels
                if l.side == LevelSide.BELOW and l.is_fresh
                and l.price < sl_price
                and sl_price - l.price <= _SL_SEARCH_DIST
            ]
            if ssl:
                nearest = max(ssl, key=lambda l: l.price)  # closest below FVG
                refined  = nearest.price - _SL_LIQ_BUFFER
                if refined > 0:
                    self.log(
                        f"  SL refined: FVG bottom {sl_price:.1f} → "
                        f"below {nearest.label} → {refined:.1f} "
                        f"({sl_price - refined:.1f}pts wider)",
                        "ENTRY",
                    )
                    sl_price = refined
        else:
            bsl = [
                l for l in self.liq_map.levels
                if l.side == LevelSide.ABOVE and l.is_fresh
                and l.price > sl_price
                and l.price - sl_price <= _SL_SEARCH_DIST
            ]
            if bsl:
                nearest = min(bsl, key=lambda l: l.price)  # closest above FVG
                refined  = nearest.price + _SL_LIQ_BUFFER
                self.log(
                    f"  SL refined: FVG top {sl_price:.1f} → "
                    f"above {nearest.label} → {refined:.1f} "
                    f"({refined - sl_price:.1f}pts wider)",
                    "ENTRY",
                )
                sl_price = refined

        if direction == "long":
            sl_points = price - sl_price
        else:
            sl_points = sl_price - price

        if sl_points <= 0 or tp_points <= 0:
            return

        # Per-trade risk cap: a single trade can never lose more than the smaller
        # of (a) max_loss_per_trade, or (b) remaining headroom before account blow.
        # This ensures one trade cannot push the account past the drawdown limit.
        remaining_headroom = abs(self.p.trailing_drawdown_max) - abs(self._total_pnl)
        effective_max_risk = max(0.0, min(self.p.max_loss_per_trade, remaining_headroom))

        if effective_max_risk <= 0:
            self.log("  RECHAZADO: Sin margen de pérdida disponible (cuenta al límite)", "WARN")
            self._rejection_counts["entry_sl_limit"] += 1
            return

        # Reject if even 1 contract's SL exceeds available headroom per contract
        if sl_points * POINT_VALUE > effective_max_risk:
            self.log(
                f"  {direction.upper()} RECHAZADO: SL ({sl_points:.1f} pts × "
                f"${POINT_VALUE}/pt = ${sl_points * POINT_VALUE:.0f}) supera headroom "
                f"${effective_max_risk:.0f}", "WARN"
            )
            self._rejection_counts["entry_sl_limit"] += 1
            return

        num_contracts = self.position_sizer.get_position_size(sl_points)
        ks_max = self.kill_switch.get_max_contracts()
        if ks_max is not None:
            num_contracts = min(num_contracts, ks_max)

        # Cap contracts so total SL loss ≤ effective_max_risk
        if sl_points * POINT_VALUE * num_contracts > effective_max_risk:
            num_contracts = max(1, int(effective_max_risk / (sl_points * POINT_VALUE)))

        if num_contracts <= 0:
            self._rejection_counts["no_contracts"] += 1
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
            self._rejection_counts["entry_preflight"] += 1
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
        self._entry_contracts = num_contracts
        self._exit_reason = ""
        self._protective_fvg = protective_fvg
        self._max_favorable_pnl = 0.0
        self._max_favorable_pct_of_tp = 0.0

        # Capture full ICT context snapshot for trade journal
        self._entry_context = self._build_entry_context(setup, price)

        # Phase 6.2 — thesis snapshot for live re-evaluation logging
        self._thesis = {
            "direction": direction,
            "entry_score": setup.total_score,
            "entry_bar": self._bar_count,
            "top_reasons": list(setup.reasons[:5]),
            "target_price": tp_price,
            "sl_price": sl_price,
            "last_opposite_dominant_bar": -1,  # tracks transient flips
        }

        if direction == "long":
            self._pending_order = self.buy(size=num_contracts)
        else:
            self._pending_order = self.sell(size=num_contracts)

    # =========================================================================
    # LIVE THESIS REVIEW — Phase 6.2
    # While in a position, keep scoring both directions and log when the
    # opposite side becomes dominant. Does NOT trigger a close — per user
    # rule, the only early-exit signal is a broken protective FVG (handled
    # in _manage_position). This is purely observability.
    # =========================================================================
    def _review_thesis(self):
        if not self.position or self._thesis is None:
            return

        price = self.data_base.close[0]
        self.scorer.set_bar(self._bar_count)
        long_bd, short_bd = self.scorer.score_both(price)

        my_dir = self._thesis["direction"]
        my_bd  = long_bd if my_dir == "long" else short_bd
        op_bd  = short_bd if my_dir == "long" else long_bd

        # Lightweight per-bar log for thesis health
        self.log(
            f"REVIEW [{my_dir.upper()}] mine={my_bd.total_score:.1f} "
            f"opp={op_bd.total_score:.1f} "
            f"entry_score={self._thesis['entry_score']:.1f}",
            "REVIEW",
        )

        # Flag if the opposite side becomes dominant (passes its threshold AND
        # outscores us by ≥0.5). Pure info — no auto-action.
        threshold = SCORER_MIN_SCORE_TRADE_2 if self.kill_switch.trades_today >= 1 else SCORER_MIN_SCORE_TRADE_1
        if (op_bd.gates_passed
                and op_bd.total_score >= threshold
                and op_bd.total_score > my_bd.total_score + 0.5):
            self._thesis["last_opposite_dominant_bar"] = self._bar_count
            self.log(
                f"⚠ THESIS CHANGED: opposite ({op_bd.direction.upper()}) now "
                f"dominant — score {op_bd.total_score:.1f} vs ours "
                f"{my_bd.total_score:.1f}. Holding per FVG-only exit rule.",
                "WARN",
            )

    # =========================================================================
    # EXIT / POSITION MANAGEMENT — Cada barra durante un trade abierto
    # =========================================================================
    def _manage_position(self):
        """
        Gestión de posición abierta — reglas del usuario:

        1. SL hard: si el precio toca el SL estructural, salir.
        2. TP completo: si el precio toca el TP, salir.
        3. 90% TP: si el PnL alcanza el 90% del TP, salir (TP confirmado).
        4. Break-even reverso: si el PnL llegó al 60% del TP y luego el
           precio se gira de vuelta hasta el entry, salir en BE (no dejar
           que vaya a SL). Si nunca alcanzó 60%, dejar correr al SL.
        5. FVG protector roto: si el FVG de 1m que aguanta el trade se
           rompe (cierre al lado contrario), salir.

        El FVG protector solo se promueve a FVGs de 1m (fallback 5m).
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

        # Track max favorable excursion for the BE-reverse rule and dashboard flag.
        if unrealized_pnl > self._max_favorable_pnl:
            self._max_favorable_pnl = unrealized_pnl
            if tp_total > 0:
                self._max_favorable_pct_of_tp = unrealized_pnl / tp_total

        # --- TRAILING FVG UPDATE (1m only, 5m fallback) ---
        # While winning, promote _protective_fvg to the closest active 1m FVG
        # that still supports the trade. If 1m has no candidates, try 5m.
        if unrealized_pnl > 0:
            trailing_trackers = [self.fvg_tracker_1m, self.fvg_tracker_5m]
            if is_long:
                closest = None
                for tr in trailing_trackers:
                    cands = [
                        f for f in tr.active_bullish
                        if f.top <= price and price - f.top <= 150
                    ]
                    if cands:
                        closest = max(cands, key=lambda f: f.top)
                        break
                if closest is not None and (
                    self._protective_fvg is None
                    or closest.top > self._protective_fvg.top
                ):
                    prev = (
                        f"{self._protective_fvg.timeframe} "
                        f"[{self._protective_fvg.bottom:.1f}–"
                        f"{self._protective_fvg.top:.1f}]"
                        if self._protective_fvg else "—"
                    )
                    self._protective_fvg = closest
                    self.log(
                        f"TRAILING FVG: {prev} → bull "
                        f"[{closest.bottom:.1f}–{closest.top:.1f}] "
                        f"({closest.timeframe})",
                        "TRAIL",
                    )
            else:
                closest = None
                for tr in trailing_trackers:
                    cands = [
                        f for f in tr.active_bearish
                        if f.bottom >= price and f.bottom - price <= 150
                    ]
                    if cands:
                        closest = min(cands, key=lambda f: f.bottom)
                        break
                if closest is not None and (
                    self._protective_fvg is None
                    or closest.bottom < self._protective_fvg.bottom
                ):
                    prev = (
                        f"{self._protective_fvg.timeframe} "
                        f"[{self._protective_fvg.bottom:.1f}–"
                        f"{self._protective_fvg.top:.1f}]"
                        if self._protective_fvg else "—"
                    )
                    self._protective_fvg = closest
                    self.log(
                        f"TRAILING FVG: {prev} → bear "
                        f"[{closest.bottom:.1f}–{closest.top:.1f}] "
                        f"({closest.timeframe})",
                        "TRAIL",
                    )

        # --- CHECK 1: Stop Loss ---
        if is_long and low <= self._sl_price:
            self.log(f"X SL HIT (LONG) @ ~{self._sl_price:.1f}", "EXIT")
            self._exit_reason = "Stop Loss"
            self.close()
            return
        elif not is_long and high >= self._sl_price:
            self.log(f"X SL HIT (SHORT) @ ~{self._sl_price:.1f}", "EXIT")
            self._exit_reason = "Stop Loss"
            self.close()
            return

        # --- CHECK 2: Take Profit completo ---
        if is_long and high >= self._tp_price:
            self.log(f"OK TP HIT (LONG) @ ~{self._tp_price:.1f}", "EXIT")
            self._exit_reason = "Take Profit"
            self.close()
            return
        elif not is_long and low <= self._tp_price:
            self.log(f"OK TP HIT (SHORT) @ ~{self._tp_price:.1f}", "EXIT")
            self._exit_reason = "Take Profit"
            self.close()
            return

        # --- CHECK 3: Break-Even reverso ---
        # Solo se arma si el trade *llegó* al 60% del TP. Si después se gira
        # y el precio vuelve al entry (PnL ≤ 0), salimos en BE en vez de
        # dejarlo ir al SL. Si nunca alcanzó 60%, no se arma — la lectura
        # estuvo errónea y dejamos que toque SL para revisar el setup.
        if (tp_total > 0
                and self._max_favorable_pnl >= tp_total * self.p.break_even_pct
                and unrealized_pnl <= 0):
            self.log(
                f"<> BREAK EVEN @ ${unrealized_pnl:.0f} — max favorable fue "
                f"${self._max_favorable_pnl:.0f} "
                f"({self._max_favorable_pct_of_tp:.0%} TP), precio volvió al entry",
                "EXIT",
            )
            self._exit_reason = "Break Even"
            self.close()
            return

        # --- CHECK 4: Ruptura del FVG protector ---
        if self._protective_fvg is not None and self._protective_fvg.status == FVGStatus.BROKEN:
            self.log(
                f"X FVG PROTECTOR ROTO ({self._protective_fvg.fvg_type.value} "
                f"{self._protective_fvg.timeframe}) — salir",
                "EXIT",
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
    # TRADE CONTEXT — Snapshot ICT setup details for journal display
    # =========================================================================
    def _build_entry_context(self, setup: "ScoreBreakdown", price: float) -> Dict:
        """
        Capture full ICT trade context at entry time.
        The resulting dict matches the TradeContext interface in lib/types.ts.
        Called from _execute_entry() immediately before placing the order.
        """
        # Market structure
        macro = self.structure_engine.get_macro_bias()
        if macro == StructureBias.BULLISH:
            market_structure = "bullish"
        elif macro == StructureBias.BEARISH:
            market_structure = "bearish"
        else:
            market_structure = "ranging"

        # Price zone (discount < 45% | equilibrium 45-55% | premium > 55%)
        hi, lo = self.liq_map.swing_range
        if hi is not None and lo is not None and hi > lo:
            pct = (price - lo) / (hi - lo)
            price_zone = "discount" if pct < 0.45 else ("premium" if pct > 0.55 else "equilibrium")
        else:
            price_zone = "equilibrium"

        # Killzone name (human-readable from KILLZONES config)
        killzone_key = self._get_current_session() or "none"
        kz = KILLZONES.get(killzone_key)
        killzone = kz.name if kz else killzone_key

        # Trigger (protective) FVG details
        prot_fvg = setup.protective_fvg
        if prot_fvg is not None:
            trigger_fvg_tf   = prot_fvg.timeframe
            trigger_fvg_type = prot_fvg.fvg_type.value   # "bullish" | "bearish"
            trigger_fvg_size = round(prot_fvg.top - prot_fvg.bottom, 1)
        else:
            trigger_fvg_tf   = "unknown"
            trigger_fvg_type = "bullish" if setup.direction == "long" else "bearish"
            trigger_fvg_size = 0.0

        # FVG confluence — active FVGs from all TFs within 300 pts of entry
        fvg_confluence = []
        _seen: set = set()
        for tracker, tf in [
            (self.fvg_tracker_4h,  "4h"),
            (self.fvg_tracker,     "base"),
            (self.fvg_tracker_15m, "15m"),
            (self.fvg_tracker_5m,  "5m"),
        ]:
            if tracker is None:
                continue
            for fvg in getattr(tracker, "_active_fvgs", []):
                dist = min(abs(fvg.top - price), abs(fvg.bottom - price))
                if dist <= 300:
                    key = (tf, fvg.fvg_type.value, round(fvg.top))
                    if key not in _seen:
                        _seen.add(key)
                        fvg_confluence.append({"timeframe": tf, "type": fvg.fvg_type.value})

        # Nearest target label
        nearest_target = "–"
        if setup.target_level is not None:
            lbl = getattr(setup.target_level, "label", "") or ""
            tp_str = f"{setup.target_level.price:.0f}"
            nearest_target = f"{lbl} @ {tp_str}" if lbl else tp_str

        # Most recent sweep (direction + price + time)
        recent_sweep: Optional[str] = None
        if self.liq_map.sweep_history:
            sw = self.liq_map.sweep_history[-1]
            ts_str = (
                sw.timestamp.strftime("%H:%M")
                if hasattr(sw.timestamp, "strftime")
                else str(sw.timestamp)
            )
            recent_sweep = f"{sw.direction} sweep @ {sw.wick_extreme:.0f} ({ts_str})"

        # Threshold used for this trade
        threshold = (
            SCORER_MIN_SCORE_TRADE_2
            if self.kill_switch.trades_today >= 1
            else SCORER_MIN_SCORE_TRADE_1
        )

        # Per-component conditions (maps to TradeSetupCondition[])
        def _pick_reason(keywords: List[str]) -> str:
            matched = [r for r in setup.reasons if any(kw in r.lower() for kw in keywords)]
            return "; ".join(matched) if matched else "—"

        conditions = [
            {
                "label":  "Sweep Quality",
                "detail": _pick_reason(["swept", "sweep", "downside", "upside", "blind"]),
                "score":  round(setup.sweep_score, 1),
                "passed": setup.has_sweep,
            },
            {
                "label":  "Structure / CHoCH",
                "detail": _pick_reason(["choch", "structure", "confirmed", "bos"]),
                "score":  round(setup.structure_score, 1),
                "passed": setup.has_choch,
            },
            {
                "label":  "FVG Path",
                "detail": _pick_reason(["fvg", "path", "obstacle", "protective", "broken", "nested", "border", "bear", "bull"]),
                "score":  round(setup.path_score, 1),
                "passed": setup.has_protective_fvg,
            },
            {
                "label":  "Target Quality",
                "detail": _pick_reason(["target", "pdh", "pdl", "rr=", "viable", "synthetic"]),
                "score":  round(setup.target_score, 1),
                "passed": setup.target_level is not None and setup.rr_filter_passed,
            },
            {
                "label":  "Macro Context",
                "detail": _pick_reason(["macro", "exhausted", "premium", "discount", "pdh consumed", "pdl consumed", "ath", "atl", "counter-trend"]),
                "score":  round(setup.macro_score, 1),
                "passed": setup.macro_score > 0,
            },
        ]

        return {
            "market_structure":       market_structure,
            "price_zone":             price_zone,
            "killzone":               killzone,
            "trigger_fvg_timeframe":  trigger_fvg_tf,
            "trigger_fvg_type":       trigger_fvg_type,
            "trigger_fvg_size_points": trigger_fvg_size,
            "fvg_confluence":         fvg_confluence,
            "nearest_target":         nearest_target,
            "recent_sweep":           recent_sweep,
            "setup_score":            round(setup.total_score, 1),
            "min_score":              round(threshold, 1),
            "conditions":             conditions,
            "exit_detail":            "",   # filled in notify_trade() at trade close
        }

    def _reset_entry_state(self):
        """Clear all entry metadata. Called when a pending order is cancelled."""
        self._entry_price = None
        self._sl_price = None
        self._tp_price = None
        self._entry_time = None
        self._entry_contracts = 0
        self._exit_reason = ""
        self._protective_fvg = None
        self._thesis = None
        self._close_pending = False
        self._entry_context = None

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

        # ── ACCOUNT BLOWN: check FIRST, before any FVG / entry logic ─────────
        # Must run before _update_fvgs() so 5m entries don't slip through.
        if self._account_blown:
            if self.position:
                self._exit_reason = "Cuenta Quemada"
                self.close()
            elif self._pending_order is not None:
                self.cancel(self._pending_order)
                self._pending_order = None
                self._reset_entry_state()
            return

        # Actualizar FVGs y liquidez
        self._update_fvgs()
        self._update_liquidity()

        # Phase 6.1 — emit MAP UPDATE if anything material changed this bar
        self._emit_map_update_if_changed()

        # Phase 7.3 — update manipulation burst state every bar
        self._update_manipulation_state()

        # Nuevo día -> actualizar contexto (sin lock de dirección)
        current_date = current_dt.date()
        if self._current_date != current_date:
            self._current_date = current_date
            self.kill_switch.new_day(current_date)
            self._update_context()
            self.fvg_tracker.cleanup_old()
            self.fvg_tracker_4h.cleanup_old()
            self.fvg_tracker_15m.cleanup_old()
            self.fvg_tracker_5m.cleanup_old()
            self.fvg_tracker_2m.cleanup_old()
            self.fvg_tracker_1m.cleanup_old()

        # Cancel pending entry orders at EOD to prevent overnight GTC carry-over.
        # A market order placed near close would fill at 09:30 AM next day,
        # resulting in H.Entrada = H.Salida = 09:30 AM with SL/TP = 0.
        if self._pending_order is not None and self._should_force_close():
            self.log(
                f"Pending entry CANCELLED at EOD — prevents GTC overnight carry-over | "
                f"ET time: {current_dt.time()}",
                "EXIT"
            )
            self.cancel(self._pending_order)
            self._pending_order = None
            self._reset_entry_state()

        # Forced close check: 4:00 PM VET (UTC-4) — no exceptions
        # Guard: skip if a close order is already pending (prevents duplicate closes
        # that would flip the position to short and produce ghost trades).
        if self.position and self._should_force_close() and not self._close_pending:
            self.log(
                f"FORCED CLOSE at VET 4:00 PM deadline | "
                f"ET time: {current_dt.time()}",
                "EXIT"
            )
            self._exit_reason = "Forced Close (VET 4PM)"
            self._forced_close_time = current_dt
            self._close_pending = True
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
            # Phase 6.2 — continuous review of thesis while in position.
            # Only NY AM: avoids spammy logs outside the kill zone. Does NOT
            # close the trade (only protective-FVG break does, in _manage_position).
            if self._get_current_session() == "ny_am":
                self._review_thesis()
            self._manage_position()
        else:
            # Do not open new positions if we're in the 5-min forced-close buffer
            if not self._should_force_close():
                # 5m FVG mitigation entries fire within the 5m update block above.
                # Fall back to 1h-based entry only when no 5m feed is available.
                if self.data_5m is None:
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

            fill_size = abs(int(order.executed.size))
            fill_price = order.executed.price

            if self.position:
                # Position is now open → this was an ENTRY fill.
                # Guarantee entry metadata is set; _execute_entry() may have
                # run on a previous bar where state was later reset.
                if self._entry_price is None:
                    self._entry_price = fill_price
                    self.log(f"  [backup] entry_price set from fill: {fill_price:.1f}", "WARN")
                if self._entry_time is None:
                    self._entry_time = self.data_base.datetime.datetime(0)
                    self.log(f"  [backup] entry_time set from fill bar", "WARN")
                if self._entry_contracts == 0:
                    self._entry_contracts = fill_size
                    self.log(f"  [backup] entry_contracts set from fill: {fill_size}", "WARN")
            else:
                # Position is now flat → this was an EXIT fill.
                # Capture exit price and rescue contracts for notify_trade().
                if self._entry_price is not None:
                    self._actual_exit_price = fill_price
                if self._entry_contracts == 0 and fill_size > 0:
                    self._entry_contracts = fill_size

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

            # Track cumulative account P&L for total trailing-drawdown limit ($2,500)
            self._total_pnl += pnl_net
            if not self._account_blown and self._total_pnl <= -abs(self.p.trailing_drawdown_max):
                self._account_blown = True
                self.log(
                    f"CUENTA QUEMADA: P&L acumulado ${self._total_pnl:+,.2f} alcanzó límite "
                    f"-${abs(self.p.trailing_drawdown_max):,.0f} — backtest detenido",
                    "RISK"
                )

            # notify_order() already rescued any missing fields from the actual
            # fill. trade.size is 0 for closed trades so we never use it.
            entry_price   = self._entry_price   if self._entry_price   is not None else trade.price
            entry_time    = self._entry_time    if self._entry_time    is not None else self.data_base.datetime.datetime(0)
            num_contracts = self._entry_contracts  # set by _execute_entry or notify_order backup

            # Use the time the forced-close was ORDERED (not when the GTC fills)
            exit_time = (
                self._forced_close_time
                if self._forced_close_time is not None
                else self.data_base.datetime.datetime(0)
            )

            if self._entry_price is None or num_contracts == 0:
                self.log(
                    f"WARN: entry metadata still missing at close — "
                    f"price={entry_price} contracts={num_contracts}",
                    "WARN",
                )

            # Finalize exit detail on the captured context snapshot
            if self._entry_context is not None:
                self._entry_context["exit_detail"] = self._exit_reason or "Manual"

            # Log del trade — incluye trazas de salida para revisión manual
            reached_60 = self._max_favorable_pct_of_tp >= self.p.break_even_pct
            self._trades_log.append({
                "timestamp": entry_time,
                "direction": "long" if trade.long else "short",
                "entry_price": entry_price,
                "exit_price": self._actual_exit_price if self._actual_exit_price is not None else self.data_base.close[0],
                "sl_price": self._sl_price,
                "tp_price": self._tp_price,
                "pnl_gross": pnl,
                "pnl_net": pnl_net,
                "commission": trade.commission,
                "contracts": num_contracts,
                "reason": self._exit_reason or "Manual",
                "entry_time": entry_time,
                "exit_time": exit_time,
                "context": self._entry_context,
                "max_favorable_pnl": float(self._max_favorable_pnl),
                "max_favorable_pct_of_tp": float(self._max_favorable_pct_of_tp),
                "reached_60pct_tp": bool(reached_60),
                "needs_review": bool(not reached_60),
            })

            # Phase 6.2 — start cooldown after a loss to prevent over-reactive flips
            if pnl_net < 0 and self.p.loss_cooldown_bars > 0:
                self._cooldown_until_bar = self._bar_count + self.p.loss_cooldown_bars
                self.log(
                    f"COOLDOWN ARMED: skip new entries until bar "
                    f"{self._cooldown_until_bar} (+{self.p.loss_cooldown_bars} bars)",
                    "TRADE",
                )

            # Reset state
            self._reset_entry_state()
            self._actual_exit_price = None
            self._forced_close_time = None
            self._close_pending = False
            self._max_favorable_pnl = 0.0
            self._max_favorable_pct_of_tp = 0.0

    # =========================================================================
    # STOP — Llamado al finalizar el backtest
    # =========================================================================
    def stop(self):
        """Genera resumen al finalizar."""
        # Always print rejection diagnostics regardless of verbose flag
        print("=" * 60)
        print("REJECTION DIAGNOSTICS (bars where entry was blocked):")
        total_rejections = sum(self._rejection_counts.values())
        for reason, count in sorted(self._rejection_counts.items(), key=lambda x: -x[1]):
            if count > 0:
                pct = count / total_rejections * 100 if total_rejections else 0
                print(f"  {reason:<28} {count:>6} bars  ({pct:.1f}%)")
        print(f"  {'TOTAL':28} {total_rejections:>6} bars")
        print("=" * 60)

        total_trades = len(self._trades_log)
        if total_trades == 0:
            print("SIN TRADES EJECUTADOS")
            print("=" * 60)
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
