"""
Liquidity Map — Full-session inventory of key liquidity levels.

Level hierarchy (weight):
  PDH / PDL               → 10
  Equal Highs / Equal Lows (= LRLR)  → 8
  Swing High / Swing Low (intraday)   → 5
  Minor swing                         → 3

Status per level:
  UNTOUCHED  — not yet reached
  SWEPT      — wick through + candle closed back (fakeout / liquidity grab)
  TAKEN      — candle closed through the level
  INVALIDATED — sweep failed: price later closed back through the swept level

Sweep "alive" rules:
  A sweep remains valid as long as:
  1. No newer sweep on the same side replaces it.
  2. Price has NOT closed back through the swept level (which would invalidate it).

Proximity framework:
  "In range" = within NY_AM_OPEN ± PROXIMITY_RANGE_POINTS.
  Target priority: nearest first, penalized by obstacle count (caller decides).
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class LiqWeight:
    PDH_PDL    = 10
    EQH_EQL    = 8     # same as LRLR
    SWING      = 5
    MINOR      = 3


class LevelStatus(Enum):
    UNTOUCHED    = "untouched"
    SWEPT        = "swept"
    TAKEN        = "taken"
    INVALIDATED  = "invalidated"


class LevelSide(Enum):
    ABOVE = "above"   # buyside
    BELOW = "below"   # sellside


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class LiquidityLevel:
    label: str
    price: float
    side: LevelSide
    weight: int
    formed_at: pd.Timestamp
    status: LevelStatus = LevelStatus.UNTOUCHED
    swept_at: Optional[pd.Timestamp] = None
    taken_at: Optional[pd.Timestamp] = None

    @property
    def is_fresh(self) -> bool:
        return self.status == LevelStatus.UNTOUCHED

    @property
    def is_swept(self) -> bool:
        return self.status == LevelStatus.SWEPT

    @property
    def is_consumed(self) -> bool:
        return self.status in (LevelStatus.SWEPT, LevelStatus.TAKEN)


@dataclass
class SweepEvent:
    """Records a single liquidity sweep (wick through + close back)."""
    level: LiquidityLevel
    timestamp: pd.Timestamp
    wick_extreme: float    # highest high (above) or lowest low (below)
    close_after: float     # close price of the sweep candle
    is_valid: bool = True  # False after price reverses back through the level

    @property
    def direction(self) -> str:
        return "upside" if self.level.side == LevelSide.ABOVE else "downside"


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------
class LiquidityMap:
    """
    Central inventory of all key levels. Updated bar by bar.
    """

    SWEEP_MIN_POINTS = 1.0   # Minimum overshoot to qualify as a wick

    def __init__(self):
        self.levels: List[LiquidityLevel] = []
        self.sweep_history: List[SweepEvent] = []
        self._ny_am_open: Optional[float] = None
        self._current_price: float = 0.0
        # ATH tracking — running max of all observed highs.
        # ATL is intentionally NOT tracked here yet; the user will provide
        # the marking methodology before that side is implemented.
        self._ath: Optional[float] = None
        self._ath_ts: Optional[pd.Timestamp] = None
        # Bars since price last printed within ATH_PROXIMITY_PTS of ATH.
        # Used to detect "post-reversal" state (price meaningfully away from ATH).
        self._bars_since_near_ath: int = 0

    # ATH proximity / reversal thresholds (points)
    ATH_PROXIMITY_PTS  = 150.0   # "near ATH" zone
    ATH_REVERSAL_PTS   = 350.0   # min distance from ATH for confirmed reversal
    ATH_BARS_TO_REVERT = 24      # bars away from ATH zone before "post-reversal"

    # ------------------------------------------------------------------
    # ATH update / accessors
    # ------------------------------------------------------------------
    def seed_ath(self, ath: float, ts: Optional[pd.Timestamp] = None) -> None:
        """Initialize ATH from historical data (e.g., precomputed from 1H feed)."""
        if self._ath is None or ath > self._ath:
            self._ath = ath
            self._ath_ts = ts

    @property
    def ath(self) -> Optional[float]:
        return self._ath

    def distance_to_ath(self, price: Optional[float] = None) -> Optional[float]:
        if self._ath is None:
            return None
        p = self._current_price if price is None else price
        return self._ath - p

    def is_near_ath(self, price: Optional[float] = None) -> bool:
        d = self.distance_to_ath(price)
        return d is not None and 0 <= d <= self.ATH_PROXIMITY_PTS

    def is_post_ath_reversal(self, price: Optional[float] = None) -> bool:
        """
        True when price is at least ATH_REVERSAL_PTS below the ATH AND
        has been outside the ATH proximity zone for ATH_BARS_TO_REVERT bars.
        Distinguishes a real pullback from a brief shake-out.
        """
        d = self.distance_to_ath(price)
        if d is None or d < self.ATH_REVERSAL_PTS:
            return False
        return self._bars_since_near_ath >= self.ATH_BARS_TO_REVERT

    # ------------------------------------------------------------------
    # Session anchor
    # ------------------------------------------------------------------
    def set_ny_am_open(self, price: float):
        self._ny_am_open = price

    # ------------------------------------------------------------------
    # Level registration
    # ------------------------------------------------------------------
    def _dedupe_add(self, level: LiquidityLevel):
        """Add level, merging with existing untouched level within 2 points."""
        for existing in self.levels:
            if (existing.side == level.side
                    and existing.status == LevelStatus.UNTOUCHED
                    and abs(existing.price - level.price) < 2.0):
                if level.weight > existing.weight:
                    existing.weight = level.weight
                    existing.label = level.label
                return
        self.levels.append(level)

    def add_pdh_pdl(self, pdh: float, pdl: float, ts: pd.Timestamp):
        self._dedupe_add(LiquidityLevel(
            f"PDH {pdh:.1f}", pdh, LevelSide.ABOVE, LiqWeight.PDH_PDL, ts))
        self._dedupe_add(LiquidityLevel(
            f"PDL {pdl:.1f}", pdl, LevelSide.BELOW, LiqWeight.PDH_PDL, ts))

    def add_equal_level(
        self, price: float, side: LevelSide, ts: pd.Timestamp, touches: int = 2
    ):
        tag = "EQH" if side == LevelSide.ABOVE else "EQL"
        self._dedupe_add(LiquidityLevel(
            f"{tag} {price:.1f} ({touches}x)", price, side,
            LiqWeight.EQH_EQL, ts))

    def add_swing(
        self, price: float, side: LevelSide, ts: pd.Timestamp, is_minor: bool = False
    ):
        w = LiqWeight.MINOR if is_minor else LiqWeight.SWING
        tag = "SwH" if side == LevelSide.ABOVE else "SwL"
        self._dedupe_add(LiquidityLevel(f"{tag} {price:.1f}", price, side, w, ts))

    # ------------------------------------------------------------------
    # Bar update
    # ------------------------------------------------------------------
    def update(self, high: float, low: float, close: float, ts: pd.Timestamp):
        """Call once per closed bar to update statuses and sweep events."""
        self._current_price = close

        # ── ATH tracking ──────────────────────────────────────────────
        if self._ath is None or high > self._ath:
            self._ath = high
            self._ath_ts = ts
        if self._ath is not None:
            if (self._ath - close) <= self.ATH_PROXIMITY_PTS:
                self._bars_since_near_ath = 0
            else:
                self._bars_since_near_ath += 1

        for lvl in self.levels:
            if not lvl.is_fresh:
                continue

            if lvl.side == LevelSide.ABOVE:
                if high >= lvl.price + self.SWEEP_MIN_POINTS:
                    if close < lvl.price:
                        # Wick through, closed back below → SWEPT
                        lvl.status = LevelStatus.SWEPT
                        lvl.swept_at = ts
                        self.sweep_history.append(SweepEvent(
                            level=lvl, timestamp=ts,
                            wick_extreme=high, close_after=close,
                        ))
                    else:
                        lvl.status = LevelStatus.TAKEN
                        lvl.taken_at = ts

            else:  # BELOW
                if low <= lvl.price - self.SWEEP_MIN_POINTS:
                    if close > lvl.price:
                        lvl.status = LevelStatus.SWEPT
                        lvl.swept_at = ts
                        self.sweep_history.append(SweepEvent(
                            level=lvl, timestamp=ts,
                            wick_extreme=low, close_after=close,
                        ))
                    else:
                        lvl.status = LevelStatus.TAKEN
                        lvl.taken_at = ts

        # Invalidate sweeps if price reverses back through the swept level
        for sw in self.sweep_history:
            if not sw.is_valid:
                continue
            lvl = sw.level
            if lvl.side == LevelSide.ABOVE and close > lvl.price:
                sw.is_valid = False
                lvl.status = LevelStatus.INVALIDATED
            elif lvl.side == LevelSide.BELOW and close < lvl.price:
                sw.is_valid = False
                lvl.status = LevelStatus.INVALIDATED

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def fresh_above(self, price: float, max_dist: float = 400.0) -> List[LiquidityLevel]:
        """Fresh levels above price, nearest first."""
        result = [
            l for l in self.levels
            if l.side == LevelSide.ABOVE and l.is_fresh
            and l.price > price and l.price - price <= max_dist
        ]
        result.sort(key=lambda l: l.price - price)
        return result

    def fresh_below(self, price: float, max_dist: float = 400.0) -> List[LiquidityLevel]:
        """Fresh levels below price, nearest first."""
        result = [
            l for l in self.levels
            if l.side == LevelSide.BELOW and l.is_fresh
            and l.price < price and price - l.price <= max_dist
        ]
        result.sort(key=lambda l: price - l.price)
        return result

    def last_valid_sweep(self, direction: str) -> Optional[SweepEvent]:
        """
        Most recent VALID sweep in the given direction.
        direction: "upside" | "downside"
        A sweep stays valid until price closes back through the swept level.
        """
        for sw in reversed(self.sweep_history):
            if sw.is_valid and sw.direction == direction:
                return sw
        return None

    def count_consumed_above(self) -> int:
        return sum(1 for l in self.levels
                   if l.side == LevelSide.ABOVE and l.is_consumed)

    def count_consumed_below(self) -> int:
        return sum(1 for l in self.levels
                   if l.side == LevelSide.BELOW and l.is_consumed)

    def upside_exhaustion(self) -> float:
        """
        0–10 score. High → most upside liquidity already taken/swept.
        Weighted by level importance.
        """
        consumed_w = sum(l.weight for l in self.levels
                         if l.side == LevelSide.ABOVE and l.is_consumed)
        fresh_w    = sum(l.weight for l in self.levels
                         if l.side == LevelSide.ABOVE and l.is_fresh)
        total = consumed_w + fresh_w
        return min(10.0, consumed_w / total * 10.0) if total > 0 else 0.0

    def downside_exhaustion(self) -> float:
        """0–10 score. High → most downside liquidity already taken/swept."""
        consumed_w = sum(l.weight for l in self.levels
                         if l.side == LevelSide.BELOW and l.is_consumed)
        fresh_w    = sum(l.weight for l in self.levels
                         if l.side == LevelSide.BELOW and l.is_fresh)
        total = consumed_w + fresh_w
        return min(10.0, consumed_w / total * 10.0) if total > 0 else 0.0

    def pdh_pdl_state(self) -> dict:
        """
        Returns the current status of the most recent PDH and PDL levels.

        Keys
        ----
        pdh_consumed  : bool — most recent PDH is swept or taken
        pdh_untouched : bool — most recent PDH is still fresh
        pdl_consumed  : bool — most recent PDL is swept or taken
        pdl_untouched : bool — most recent PDL is still fresh
        """
        pdh = pdl = None
        for lvl in self.levels:
            if lvl.side == LevelSide.ABOVE and lvl.weight == LiqWeight.PDH_PDL:
                if pdh is None or lvl.formed_at > pdh.formed_at:
                    pdh = lvl
            elif lvl.side == LevelSide.BELOW and lvl.weight == LiqWeight.PDH_PDL:
                if pdl is None or lvl.formed_at > pdl.formed_at:
                    pdl = lvl
        return {
            "pdh_consumed":  pdh is not None and pdh.is_consumed,
            "pdh_untouched": pdh is not None and pdh.is_fresh,
            "pdl_consumed":  pdl is not None and pdl.is_consumed,
            "pdl_untouched": pdl is not None and pdl.is_fresh,
        }

    # ------------------------------------------------------------------
    # Day reset
    # ------------------------------------------------------------------
    def reset_intraday(self):
        """
        Called at the start of each trading day.
        Keeps PDH/PDL and EQH/EQL; discards intraday swing levels.
        """
        self.levels = [
            l for l in self.levels
            if l.weight >= LiqWeight.EQH_EQL
        ]
        self.sweep_history.clear()
        self._ny_am_open = None
