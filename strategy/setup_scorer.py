"""
Setup Scorer — "Sum of ingredients" approach for ICT trade setups.

Philosophy (per the trading manual):
  - The bot evaluates BOTH long AND short every bar.
  - Direction is decided by which setup scores higher (if either meets threshold).
  - The macro 4H bias is CONTEXT, never a hard gate.
  - A counter-trend short is valid if upside liquidity is exhausted, key bullish
    FVGs are broken, and fresh sellside liquidity is accessible below.

Scoring categories:
  1. Sweep quality       — was the right side taken? (PDH > EQH > Swing)
  2. Structure / CHoCH   — candle-close confirmed CHoCH in confirmation TF
  3. FVG path analysis   — are key opposing FVGs broken? is the path clear?
  4. Target quality      — what are we shooting at, and how close?
  5. Macro alignment     — 4H / 1H context bonus (never a penalty for counter-trend)

Hard gates (all must pass to allow entry):
  A. At least one valid sweep on the opposing side
  B. CHoCH confirmed (close-based) on at least one confirmation TF
  C. A protective FVG exists for SL placement

Thresholds:
  First trade of day  → MIN_SCORE_TRADE_1 (default 8.0)
  Second trade of day → MIN_SCORE_TRADE_2 (default 12.0)

TP selection logic:
  - Primary target = nearest fresh liquidity level in trade direction
  - Skip target if more than MAX_OBSTACLES_IN_PATH intact higher-TF FVGs sit
    between price and that target
  - Next viable target is selected instead
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generator, List, Optional, Tuple

import pandas as pd

from indicators.structure_engine import StructureEngine, StructureBias
from indicators.liquidity_map import LiquidityMap, LiquidityLevel, LevelSide, LevelStatus, LiqWeight, SweepEvent
from indicators.fvg import FVGTracker, FVGType, FVGStatus, FairValueGap
from config.settings import (
    SCORER_MIN_SCORE_TRADE_1 as MIN_SCORE_TRADE_1,
    SCORER_MIN_SCORE_TRADE_2 as MIN_SCORE_TRADE_2,
    SCORER_PROXIMITY_RANGE_POINTS as PROXIMITY_RANGE,
    SCORER_MAX_PATH_OBSTACLES as MAX_OBSTACLES_HT,
    SCORER_CHOCH_LOOKBACK_BARS as CHOCH_LOOKBACK,
)

MIN_TP_DISTANCE_PTS = 25.0   # Hard filter: TP must be ≥ 25 points from entry
MIN_RR_RATIO        = 1.0    # Hard filter: R:R must be ≥ 1:1

# Tie-breaking guard for ATH bonus: if both directions are within this delta
# in raw score, the ATH context bonus is suppressed (would otherwise decide
# direction by itself).
ATH_TIE_BREAK_DELTA = 0.5

# Phase 2 — Broken FVG weighting (Option D)
# Per-TF contribution cap is BROKEN_WEIGHT * BROKEN_MAX_PER_TF (so 1H caps at 2.0).
BROKEN_FVG_WEIGHT = {"4h": 1.5, "base": 1.0, "15m": 0.5, "5m": 0.3, "1m": 0.3}
BROKEN_MAX_PER_TF = 2.0     # multiplier cap on per-TF weight
TF_RANK = {"5m": 1, "15m": 2, "base": 3, "4h": 4, "1m": 0}
DAMPENING_FACTOR = 0.7      # 30% dampening when higher-TF intact FVG ahead
ALIGNMENT_TOLERANCE = 10.0  # points tolerance for "approximately same" boundary
ALIGNMENT_BONUS     = 0.5


# ---------------------------------------------------------------------------
# Score breakdown
# ---------------------------------------------------------------------------
@dataclass
class ScoreBreakdown:
    direction: str                              # "long" | "short"
    total_score: float = 0.0

    # Component scores
    sweep_score: float     = 0.0
    structure_score: float = 0.0
    path_score: float      = 0.0
    target_score: float    = 0.0
    macro_score: float     = 0.0

    # Hard gates
    has_sweep:          bool = False
    has_choch:          bool = False
    has_protective_fvg: bool = False
    rr_filter_passed:   bool = True   # False = hard reject on R:R or TP distance

    # R:R metrics (populated when both target and protective FVG are known)
    rr_ratio:    float = 0.0
    tp_distance: float = 0.0

    # ATH context bonus, computed during scoring but applied conditionally
    # (suppressed if the long vs short raw score gap is < ATH_TIE_BREAK_DELTA).
    pending_ath_bonus: float = 0.0
    pending_ath_reason: str  = ""

    # Selected levels (filled in if gates pass)
    target_level:    Optional[LiquidityLevel] = None
    protective_fvg:  Optional[FairValueGap]   = None

    reasons: List[str] = field(default_factory=list)

    @property
    def gates_passed(self) -> bool:
        return (
            self.has_choch
            and self.has_protective_fvg
            and self.target_level is not None
            and self.rr_filter_passed
        )

    def log_str(self) -> str:
        """One-line summary with per-gate PASS/FAIL and score breakdown."""
        sweep = "PASS" if self.has_sweep          else "FAIL"
        choch = "PASS" if self.has_choch          else "FAIL"
        fvg   = "PASS" if self.has_protective_fvg else "FAIL"
        tgt   = "PASS" if self.target_level is not None else "FAIL"
        rr    = "PASS" if self.rr_filter_passed   else "FAIL"
        gates = f"[Swp:{sweep} CHoCH:{choch} FVG:{fvg} Tgt:{tgt} RR:{rr}]"
        scores = (
            f"swp={self.sweep_score:.1f} str={self.structure_score:.1f} "
            f"path={self.path_score:.1f} tgt={self.target_score:.1f} "
            f"mac={self.macro_score:.1f}"
        )
        rr_str = f"RR={self.rr_ratio:.2f}:1 tp={self.tp_distance:.1f}pts"
        return (
            f"{self.direction.upper()} {gates} "
            f"TOTAL={self.total_score:.1f} [{scores}] {rr_str}"
        )

    def rejection_reason(self) -> str:
        """Short description of why this setup was rejected (empty if valid)."""
        if self.gates_passed:
            return ""
        parts = []
        if not self.has_choch:
            parts.append("no CHoCH confirmed")
        if not self.has_protective_fvg:
            parts.append("no protective FVG")
        if self.target_level is None:
            parts.append("no viable target (no fresh levels within 400pts)")
        if not self.rr_filter_passed:
            parts.append(
                f"R:R failed (tp={self.tp_distance:.1f}pts min={MIN_TP_DISTANCE_PTS:.0f} "
                f"| rr={self.rr_ratio:.2f} min={MIN_RR_RATIO:.1f})"
            )
        return " | ".join(parts) if parts else "score below threshold"


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------
class SetupScorer:
    """
    Evaluates long and short setups each bar.
    Needs:
      - structure_engine : StructureEngine (tracking "4h" and "base" at minimum)
      - liq_map          : LiquidityMap
      - fvg_high         : FVGTracker for the higher TF (4H or 1H) — obstacles
      - fvg_base         : FVGTracker for the base / entry TF (15m or 5m) — confirmations
    """

    def __init__(
        self,
        structure_engine: StructureEngine,
        liq_map: LiquidityMap,
        fvg_high: FVGTracker,
        fvg_base: FVGTracker,
        fvg_15m: Optional[FVGTracker] = None,
        fvg_5m: Optional[FVGTracker] = None,
    ):
        self.structure  = structure_engine
        self.liq_map    = liq_map
        self.fvg_high   = fvg_high   # 4H: path obstacles & short protective FVG
        self.fvg_base   = fvg_base   # 1H: base confirmations
        self.fvg_15m    = fvg_15m    # 15m (optional): finer entry confirmations
        self.fvg_5m     = fvg_5m     # 5m (optional): finest entry confirmations
        self._current_bar: int = 0   # updated via set_bar() each bar

    def _entry_trackers(self) -> Generator[Tuple[FVGTracker, str], None, None]:
        """Yield (tracker, tf_name) from finest to coarsest entry-TF."""
        for tracker, name in [(self.fvg_5m, "5m"), (self.fvg_15m, "15m"), (self.fvg_base, "base")]:
            if tracker is not None:
                yield tracker, name

    def _nesting_bonus(self, fvg: FairValueGap, direction: str) -> float:
        """
        Returns a confluence bonus when the entry FVG is nested inside
        higher-TF FVGs of the same type (ICT nested order block / FVG concept).
        A 5m FVG sitting inside a 1H FVG sitting inside a 4H FVG = high probability.
        """
        ht_active = self.fvg_high.active_bullish if direction == "long" else self.fvg_high.active_bearish
        containing = [
            f for f in ht_active
            if f.bottom <= fvg.bottom and fvg.top <= f.top
        ]
        if len(containing) >= 2:
            return 1.5
        if len(containing) == 1:
            return 1.0
        return 0.0

    def _all_trackers(self) -> List[Tuple[Optional[FVGTracker], str]]:
        """All FVG trackers paired with their TF name (highest → lowest)."""
        return [
            (self.fvg_high, "4h"),
            (self.fvg_base, "base"),   # base = 1H in this codebase
            (self.fvg_15m,  "15m"),
            (self.fvg_5m,   "5m"),
        ]

    def _broken_fvg_path_score(
        self, price: float, direction: str
    ) -> Tuple[float, List[str]]:
        """
        Option D: per-TF weighted contribution from broken opposing FVGs,
        with 30% dampening when an intact higher-TF FVG of the SAME type
        is still in the path ahead.

        For LONG: counts broken BEARISH FVGs (path opening upwards).
                  Dampened if intact bearish FVG above price at higher TF.
        For SHORT: counts broken BULLISH FVGs (path opening downwards).
                   Dampened if intact bullish FVG below price at higher TF.

        Returns (total_score, reason_strings).
        """
        if direction == "long":
            broken_type = FVGType.BEARISH
            in_path = lambda f: f.bottom >= price   # bear FVG above price
        else:
            broken_type = FVGType.BULLISH
            in_path = lambda f: f.top <= price      # bull FVG below price

        trackers = self._all_trackers()
        score = 0.0
        reasons: List[str] = []

        for tracker, tf_name in trackers:
            if tracker is None:
                continue
            # Use broken_fvgs directly — avoids iterating active FVGs.
            broken = [f for f in tracker.broken_fvgs if f.fvg_type == broken_type]
            if not broken:
                continue

            weight = BROKEN_FVG_WEIGHT.get(tf_name, 0.0)
            count_capped = min(len(broken), BROKEN_MAX_PER_TF)
            contribution = weight * count_capped

            # Dampening: any HIGHER-TF tracker with an intact same-type FVG
            # still in the path? Use active sub-lists to avoid scanning broken FVGs.
            my_rank = TF_RANK.get(tf_name, 0)
            damp = False
            for ot_tracker, ot_name in trackers:
                if ot_tracker is None:
                    continue
                if TF_RANK.get(ot_name, 0) <= my_rank:
                    continue
                ot_active = (ot_tracker.active_bearish if broken_type == FVGType.BEARISH
                             else ot_tracker.active_bullish)
                if any(in_path(f) for f in ot_active):
                    damp = True
                    break

            if damp:
                contribution *= DAMPENING_FACTOR
                reasons.append(
                    f"{tf_name}: {len(broken)} broken {broken_type.value} "
                    f"(dampened ×{DAMPENING_FACTOR}) → +{contribution:.2f}"
                )
            else:
                reasons.append(
                    f"{tf_name}: {len(broken)} broken {broken_type.value} → "
                    f"+{contribution:.2f}"
                )
            score += contribution

        return score, reasons

    def _border_alignment_bonus(
        self, protective_fvg: Optional[FairValueGap], direction: str
    ) -> Tuple[float, str]:
        """
        Bonus when the protective (smaller-TF) FVG shares a boundary —
        within ALIGNMENT_TOLERANCE points — with an OPPOSING FVG at a
        HIGHER TF. Captures the "fake-out / breakdown entry" scenario:
        smaller FVG's break aligns with a larger FVG's edge.

        Recursive across all TF pairs (5m↔15m, 15m↔base, base↔4h, etc).
        """
        if protective_fvg is None:
            return 0.0, ""

        opposing = FVGType.BEARISH if direction == "long" else FVGType.BULLISH
        prot_tf = protective_fvg.timeframe
        prot_rank = TF_RANK.get(prot_tf, 0)
        p_top = protective_fvg.top
        p_bot = protective_fvg.bottom

        for tracker, tf_name in self._all_trackers():
            if tracker is None:
                continue
            if TF_RANK.get(tf_name, 0) <= prot_rank:
                continue   # only LARGER TFs
            # Use active sub-list to avoid scanning broken FVGs unnecessarily
            candidates = tracker.active_bearish if opposing == FVGType.BEARISH else tracker.active_bullish
            for f in candidates:
                if (abs(f.top    - p_top) <= ALIGNMENT_TOLERANCE
                    or abs(f.bottom - p_bot) <= ALIGNMENT_TOLERANCE
                    or abs(f.top    - p_bot) <= ALIGNMENT_TOLERANCE
                    or abs(f.bottom - p_top) <= ALIGNMENT_TOLERANCE):
                    return ALIGNMENT_BONUS, (
                        f"Border alignment {prot_tf}↔{tf_name} (opposing "
                        f"{opposing.value}) → +{ALIGNMENT_BONUS:.1f}"
                    )

        return 0.0, ""

    def _sweep_quality_multiplier(
        self, sw: SweepEvent, direction: str
    ) -> Tuple[float, str]:
        """
        Phase 7.2 — Sweep quality gate.

        Returns (multiplier, reason):
          1.0 → quality sweep: an opposing FVG in the wick zone confirms the
                rejection (institutional-level price acceptance).
          0.5 → blind sweep:  no FVG context at the wick extreme → halved score.

        For SHORT (upside sweep):
          Key BEARISH higher-TF FVGs whose range overlaps the wick zone
          [sweep_level, wick_extreme] — they are the supply that "caught" price
          and sent it back. If none remain active there, the sweep is unanchored.

        For LONG (downside sweep):
          Key BULLISH higher-TF FVGs in the wick zone [wick_extreme, sweep_level]
          — the demand that absorbed the wick and bounced price.
        """
        sw_price = sw.level.price
        wick     = sw.wick_extreme

        if direction == "short":
            zone_lo = sw_price - 20
            zone_hi = wick + 20
            key_fvgs = [
                f for f in self.fvg_high.active_bearish
                if f.bottom <= zone_hi and f.top >= zone_lo
            ]
            if key_fvgs:
                return 1.0, (
                    f"Quality sweep: {len(key_fvgs)} bearish FVG(s) intact "
                    f"in wick zone [{sw_price:.0f}–{wick:.0f}]"
                )
            return 0.7, "Blind sweep: no bearish FVG in wick zone → score ×0.7"

        else:  # long / downside sweep
            zone_lo = wick - 20
            zone_hi = sw_price + 20
            key_fvgs = [
                f for f in self.fvg_high.active_bullish
                if f.bottom <= zone_hi and f.top >= zone_lo
            ]
            if key_fvgs:
                return 1.0, (
                    f"Quality sweep: {len(key_fvgs)} bullish FVG(s) intact "
                    f"in wick zone [{wick:.0f}–{sw_price:.0f}]"
                )
            return 0.7, "Blind sweep: no bullish FVG in wick zone → score ×0.7"

    def set_bar(self, bar_idx: int):
        """Call once per bar so significance scores use correct age."""
        self._current_bar = bar_idx

    # Timeframe weights for significance_score()
    _TF_WEIGHT = {"4h": 4.0, "1h": 3.0, "15m": 2.0, "5m": 1.0, "base": 3.0}

    def _sig(self, fvg, tf: str = "base") -> float:
        """Shorthand: significance score for an FVG at the current bar."""
        return fvg.significance_score(self._current_bar, self._TF_WEIGHT.get(tf, 1.0))

    def _compute_ath_bonus(self, bd: ScoreBreakdown, price: float) -> None:
        """
        Phase 8.1 — Symmetric ATH / ATL proximity bonus (no macro condition).

        Rules:
          - LONG:  ATH within 350 pts → +1.0
                   (price near all-time high = upside momentum context)
          - SHORT: ATL within 350 pts → +1.0
                   (price near 30-day rolling low = downside momentum context)

        Stored as pending; applied via _apply_pending_ath_bonuses() with the
        tie-break guard (suppressed when scores are within ATH_TIE_BREAK_DELTA).
        """
        if bd.direction == "long":
            if self.liq_map.is_near_ath(price):
                d = self.liq_map.distance_to_ath(price) or 0.0
                bd.pending_ath_bonus  = 1.0
                bd.pending_ath_reason = f"Near ATH ({d:.0f}pts) → +1.0"
        else:  # short
            if self.liq_map.is_near_atl(price):
                d = self.liq_map.distance_to_atl(price) or 0.0
                bd.pending_ath_bonus  = 1.0
                bd.pending_ath_reason = f"Near ATL ({d:.0f}pts) → +1.0"

    def _discount_premium_bonus(self, bd: ScoreBreakdown, price: float) -> None:
        """
        Phase 8.2 — Discount / premium zone bonus.

        Uses the current intraday swing range (set via LiquidityMap.set_swing_range).
          - LONG  in discount zone (price < 50% of range) → +1.0
          - SHORT in premium zone  (price > 50% of range) → +1.0

        No bonus if the swing range is not yet established.
        """
        hi, lo = self.liq_map.swing_range
        if hi is None or lo is None or hi <= lo:
            return
        pct = (price - lo) / (hi - lo)  # 0.0 = at swing low, 1.0 = at swing high
        if bd.direction == "long" and pct < 0.50:
            bd.macro_score += 1.0
            bd.reasons.append(f"Discount zone ({pct:.0%} of swing range) → +1.0")
        elif bd.direction == "short" and pct > 0.50:
            bd.macro_score += 1.0
            bd.reasons.append(f"Premium zone ({pct:.0%} of swing range) → +1.0")

    def _apply_pending_ath_bonuses(
        self, long_bd: ScoreBreakdown, short_bd: ScoreBreakdown
    ) -> None:
        """
        Apply the per-direction pending ATH bonus, except when the raw
        score gap is below ATH_TIE_BREAK_DELTA (caveat: don't let ATH
        decide direction in a near-tie).
        """
        gap = abs(long_bd.total_score - short_bd.total_score)
        if gap < ATH_TIE_BREAK_DELTA:
            for bd in (long_bd, short_bd):
                if bd.pending_ath_bonus != 0.0:
                    bd.reasons.append(
                        f"ATH bonus SUPPRESSED (tie-break: |Δ|={gap:.2f} < "
                        f"{ATH_TIE_BREAK_DELTA})"
                    )
                    bd.pending_ath_bonus = 0.0
                    bd.pending_ath_reason = ""
            return

        for bd in (long_bd, short_bd):
            if bd.pending_ath_bonus != 0.0:
                bd.macro_score += bd.pending_ath_bonus
                bd.total_score += bd.pending_ath_bonus
                bd.reasons.append(bd.pending_ath_reason)
                bd.pending_ath_bonus = 0.0
                bd.pending_ath_reason = ""

    def _apply_rr_filter(
        self, bd: ScoreBreakdown, price: float, sl_price: float, tp_price: float
    ) -> None:
        """
        Applies R:R hard filters and score adjustments to bd in place.

        Hard filters (if either fails → rr_filter_passed = False):
          - TP distance < MIN_TP_DISTANCE_PTS (25 pts absolute)
          - R:R < MIN_RR_RATIO (1:1)

        Score bonus/penalty on bd.target_score:
          - R:R >= 3:1  → +1.0
          - R:R >= 2:1  → +0.5
          - R:R <  1.5  → -1.0 (poor but still valid above min threshold)
        """
        if sl_price <= 0 or tp_price <= 0:
            return

        sl_dist = abs(price - sl_price)
        tp_dist = abs(tp_price - price)

        bd.tp_distance = tp_dist
        bd.rr_ratio = tp_dist / sl_dist if sl_dist > 0 else 0.0

        if tp_dist < MIN_TP_DISTANCE_PTS or bd.rr_ratio < MIN_RR_RATIO:
            bd.rr_filter_passed = False
            bd.reasons.append(
                f"RR FAIL: tp={tp_dist:.1f}pts rr={bd.rr_ratio:.2f}:1"
            )
            return

        if bd.rr_ratio >= 3.0:
            bd.target_score += 1.0
            bd.reasons.append(f"RR={bd.rr_ratio:.1f}:1 → +1.0")
        elif bd.rr_ratio >= 2.0:
            bd.target_score += 0.5
            bd.reasons.append(f"RR={bd.rr_ratio:.1f}:1 → +0.5")
        elif bd.rr_ratio < 1.5:
            bd.target_score -= 1.0
            bd.reasons.append(f"RR={bd.rr_ratio:.1f}:1 → -1.0 (poor RR)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def best_setup(
        self, price: float, trades_today: int
    ) -> Optional[ScoreBreakdown]:
        """
        Return the highest-scoring valid setup, or None if nothing qualifies.
        """
        threshold = MIN_SCORE_TRADE_2 if trades_today >= 1 else MIN_SCORE_TRADE_1
        long_bd  = self._score_long(price)
        short_bd = self._score_short(price)
        self._apply_pending_ath_bonuses(long_bd, short_bd)

        candidates = [
            bd for bd in (long_bd, short_bd)
            if bd.gates_passed and bd.total_score >= threshold
        ]
        return max(candidates, key=lambda bd: bd.total_score) if candidates else None

    def score_both(
        self, price: float
    ) -> Tuple[ScoreBreakdown, ScoreBreakdown]:
        long_bd  = self._score_long(price)
        short_bd = self._score_short(price)
        self._apply_pending_ath_bonuses(long_bd, short_bd)
        return long_bd, short_bd

    # ------------------------------------------------------------------
    # LONG scoring
    # ------------------------------------------------------------------
    def _score_long(self, price: float) -> ScoreBreakdown:
        bd = ScoreBreakdown(direction="long")

        # ── GATE A: valid downside sweep ──────────────────────────────
        sw = self.liq_map.last_valid_sweep("downside")
        if sw:
            bd.has_sweep = True
            w = sw.level.weight
            if w >= LiqWeight.PDH_PDL:
                bd.sweep_score = 3.0
                bd.reasons.append(f"PDL swept ({sw.level.label})")
            elif w >= LiqWeight.EQH_EQL:
                bd.sweep_score = 2.0
                bd.reasons.append(f"EQL swept ({sw.level.label})")
            else:
                bd.sweep_score = 1.0
                bd.reasons.append(f"Swing swept ({sw.level.label})")
            extra = max(0, self.liq_map.count_consumed_below() - 1)
            if extra:
                bd.sweep_score += min(1.5, extra * 0.5)
                bd.reasons.append(f"+{extra} extra downside levels consumed")

            # Phase 7.2 — sweep quality gate
            mult, q_reason = self._sweep_quality_multiplier(sw, "long")
            if mult < 1.0:
                bd.sweep_score *= mult
            bd.reasons.append(q_reason)

        # ── GATE B: CHoCH bullish (close-confirmed) ───────────────────
        if self.structure.had_confirmation_choch(
            "bullish", CHOCH_LOOKBACK, confirmation_tfs=["4h", "1h", "base", "15m", "5m", "1m"]
        ):
            bd.has_choch = True
            bd.structure_score = 3.0
            bd.reasons.append("CHoCH bullish confirmed")
            # Multi-TF bonus
            confirmed_tfs = [
                tf for tf in ("4h", "1h", "base", "15m", "5m", "1m")
                if tf in self.structure.trackers
                and self.structure.trackers[tf].had_choch_recently("bullish", CHOCH_LOOKBACK)
            ]
            if len(confirmed_tfs) >= 2:
                bd.structure_score += 1.0
                bd.reasons.append(f"CHoCH on {confirmed_tfs}")

        # ── FVG PATH (LONG) ───────────────────────────────────────────
        # Higher-TF bearish FVGs above price = obstacles (weighted by significance)
        ht_bear_above = [f for f in self.fvg_high.active_bearish if f.bottom >= price]
        obstacle_w = sum(self._sig(f, "4h") for f in ht_bear_above)

        if obstacle_w == 0:
            bd.path_score += 3.0
            bd.reasons.append("No higher-TF bearish FVGs above (clear path)")
        elif obstacle_w < 2.5:
            bd.path_score += 1.5
            bd.reasons.append(f"Light bear obstacle weight={obstacle_w:.1f}")
        elif obstacle_w < 5.0:
            bd.path_score += 0.5
            bd.reasons.append(f"Moderate bear obstacles weight={obstacle_w:.1f}")
        else:
            bd.path_score -= 1.0
            bd.reasons.append(f"Heavy bear obstacles weight={obstacle_w:.1f} (PENALTY)")

        # Broken bearish FVGs → path opening (Option D, weighted by TF + dampening)
        bf_score, bf_reasons = self._broken_fvg_path_score(price, "long")
        if bf_score > 0:
            bd.path_score += bf_score
            bd.reasons.extend(bf_reasons)

        # Gate C: protective bullish FVG below price for SL.
        # Prefer finest TF (tightest SL), fall back to higher-TF.
        for tracker, tf_name in self._entry_trackers():
            candidates = [
                f for f in tracker.active_bullish
                if f.top <= price and price - f.top <= 250
            ]
            if candidates:
                candidates.sort(key=lambda f: price - f.top)
                bd.protective_fvg = candidates[0]
                bd.has_protective_fvg = True
                bd.path_score += 1.0
                bd.reasons.append(
                    f"Protective bull FVG ({tf_name}) @ "
                    f"{candidates[0].top:.1f}-{candidates[0].bottom:.1f}"
                )
                break
        else:
            # Last resort: higher-TF bullish FVG below price
            ht_bull_below = self.fvg_high.get_nearest_protective_fvg(price, "long")
            if ht_bull_below:
                bd.protective_fvg = ht_bull_below
                bd.has_protective_fvg = True
                bd.reasons.append(f"Protective higher-TF bull FVG @ {ht_bull_below.top:.1f}")
            else:
                bd.reasons.append("No protective FVG (GATE C fail)")

        # Nested FVG confluence bonus
        if bd.protective_fvg is not None:
            bonus = self._nesting_bonus(bd.protective_fvg, "long")
            if bonus > 0:
                bd.path_score += bonus
                bd.reasons.append(f"Nested FVG confluence (long) +{bonus:.1f}")

        # Border alignment bonus — fake-out / breakdown entry signal
        if bd.protective_fvg is not None:
            align_bonus, align_reason = self._border_alignment_bonus(
                bd.protective_fvg, "long"
            )
            if align_bonus > 0:
                bd.path_score += align_bonus
                bd.reasons.append(align_reason)

        # ── TARGET SELECTION (LONG) ───────────────────────────────────
        targets = self.liq_map.fresh_above(price, PROXIMITY_RANGE)
        _ht_bear_active = self.fvg_high.active_bearish
        viable: List[Tuple[LiquidityLevel, int]] = []
        for t in targets:
            obstacles = sum(
                1 for f in _ht_bear_active if price < f.midpoint < t.price
            )
            if obstacles <= MAX_OBSTACLES_HT:
                viable.append((t, obstacles))

        if viable:
            best, obs = viable[0]
            bd.target_level = best
            if best.weight >= LiqWeight.PDH_PDL:
                bd.target_score = 2.5
                bd.reasons.append(f"Target PDH {best.price:.1f}")
            elif best.weight >= LiqWeight.EQH_EQL:
                bd.target_score = 2.0
                bd.reasons.append(f"Target EQH {best.price:.1f}")
            else:
                bd.target_score = 1.0
                bd.reasons.append(f"Target SwH {best.price:.1f}")
            if len(viable) >= 2:
                bd.target_score += 0.5
                bd.reasons.append(f"+{len(viable)-1} more viable targets above")
            bd.target_score -= obs * 0.5
        elif bd.protective_fvg is not None:
            # Fallback: synthetic 2:1 TP anchored to the protective FVG bottom
            sl_dist = price - bd.protective_fvg.bottom
            if sl_dist > 0:
                synthetic_tp = price + sl_dist * 2.0
                bd.target_level = LiquidityLevel(
                    label="Synthetic 2:1 TP",
                    price=synthetic_tp,
                    side=LevelSide.ABOVE,
                    weight=3,
                    formed_at=pd.Timestamp.now(),
                    status=LevelStatus.UNTOUCHED,
                )
                bd.target_score = 0.5
                bd.reasons.append(
                    f"Synthetic 2:1 target @ {synthetic_tp:.1f} "
                    f"(no fresh levels in {PROXIMITY_RANGE:.0f}pt range)"
                )
        else:
            bd.reasons.append("No viable target above")

        # ── MACRO ALIGNMENT (LONG) ────────────────────────────────────
        macro = self.structure.get_macro_bias()
        if macro == StructureBias.BULLISH:
            bd.macro_score += 1.0
            bd.reasons.append("Macro (4H) bullish ✓")
        elif macro == StructureBias.BEARISH:
            bd.reasons.append("Counter-trend long (macro bearish)")

        base_bias = self.structure.get_bias("base")
        if base_bias == StructureBias.BULLISH:
            bd.macro_score += 0.5

        exhaustion = self.liq_map.downside_exhaustion()
        if exhaustion >= 7.0:
            bd.macro_score += 1.0
            bd.reasons.append(f"Downside exhausted {exhaustion:.1f}/10")
        elif exhaustion >= 4.0:
            bd.macro_score += 0.5

        # Phase 7.1 — PDH/PDL state bonus (macro-conditioned)
        pdh_pdl = self.liq_map.pdh_pdl_state()
        if (pdh_pdl["pdl_consumed"] and pdh_pdl["pdh_untouched"]
                and macro != StructureBias.BEARISH):
            bd.macro_score += 1.0
            bd.reasons.append("PDL consumed + PDH untouched → bullish liquidity skew +1.0")

        # Phase 8.2 — Discount / premium zone bonus
        self._discount_premium_bonus(bd, price)

        # ── R:R FILTER (LONG) ─────────────────────────────────────────
        if bd.target_level is not None and bd.protective_fvg is not None:
            self._apply_rr_filter(
                bd, price,
                sl_price=bd.protective_fvg.bottom,
                tp_price=bd.target_level.price,
            )

        # ── ATH CONTEXT (LONG) ────────────────────────────────────────
        # Stored as pending; applied in best_setup/score_both with tie-break.
        self._compute_ath_bonus(bd, price)

        bd.total_score = (
            bd.sweep_score + bd.structure_score
            + bd.path_score + bd.target_score + bd.macro_score
        )
        return bd

    # ------------------------------------------------------------------
    # SHORT scoring
    # ------------------------------------------------------------------
    def _score_short(self, price: float) -> ScoreBreakdown:
        bd = ScoreBreakdown(direction="short")

        # ── GATE A: valid upside sweep ────────────────────────────────
        sw = self.liq_map.last_valid_sweep("upside")
        if sw:
            bd.has_sweep = True
            w = sw.level.weight
            if w >= LiqWeight.PDH_PDL:
                bd.sweep_score = 3.0
                bd.reasons.append(f"PDH swept ({sw.level.label})")
            elif w >= LiqWeight.EQH_EQL:
                bd.sweep_score = 2.0
                bd.reasons.append(f"EQH swept ({sw.level.label})")
            else:
                bd.sweep_score = 1.0
                bd.reasons.append(f"Swing swept ({sw.level.label})")
            extra = max(0, self.liq_map.count_consumed_above() - 1)
            if extra:
                bd.sweep_score += min(1.5, extra * 0.5)
                bd.reasons.append(f"+{extra} extra upside levels consumed")

            # Phase 7.2 — sweep quality gate
            mult, q_reason = self._sweep_quality_multiplier(sw, "short")
            if mult < 1.0:
                bd.sweep_score *= mult
            bd.reasons.append(q_reason)

        # ── GATE B: CHoCH bearish (close-confirmed) ───────────────────
        if self.structure.had_confirmation_choch(
            "bearish", CHOCH_LOOKBACK, confirmation_tfs=["4h", "1h", "base", "15m", "5m", "1m"]
        ):
            bd.has_choch = True
            bd.structure_score = 3.0
            bd.reasons.append("CHoCH bearish confirmed")
            confirmed_tfs = [
                tf for tf in ("4h", "1h", "base", "15m", "5m", "1m")
                if tf in self.structure.trackers
                and self.structure.trackers[tf].had_choch_recently("bearish", CHOCH_LOOKBACK)
            ]
            if len(confirmed_tfs) >= 2:
                bd.structure_score += 1.0
                bd.reasons.append(f"CHoCH on {confirmed_tfs}")

        # ── FVG PATH (SHORT) ──────────────────────────────────────────
        # Higher-TF bullish FVGs below price = obstacles (weighted by significance)
        ht_bull_below = [f for f in self.fvg_high.active_bullish if f.top <= price]
        ht_bull_below.sort(key=lambda f: price - f.top)

        # Broken bullish FVGs → path opening (Option D, weighted by TF + dampening)
        # Symmetric with long-side scoring; replaces the previous asymmetric
        # +4.0 short-only bonus.
        bf_score, bf_reasons = self._broken_fvg_path_score(price, "short")
        if bf_score > 0:
            bd.path_score += bf_score
            bd.reasons.extend(bf_reasons)

        # Immediate path: significance-weighted obstacle score within 100 pts
        immediate = [f for f in ht_bull_below if price - f.top <= 100]
        immediate_w = sum(self._sig(f, "4h") for f in immediate)
        if immediate_w == 0:
            bd.path_score += 2.0
            bd.reasons.append("No higher-TF bull FVG in immediate 100-pt path")
        elif immediate_w < 2.5:
            bd.path_score += 0.5
            bd.reasons.append(f"Light immediate obstacle weight={immediate_w:.1f}")
        else:
            bd.path_score -= 1.0
            bd.reasons.append(f"Heavy immediate obstacles weight={immediate_w:.1f} (PENALTY)")

        # Bearish FVGs above price in finest available TF = downward intent
        for tracker, tf_name in self._entry_trackers():
            bear_fine_above = [f for f in tracker.active_bearish if f.bottom >= price]
            if bear_fine_above:
                bd.path_score += min(2.0, len(bear_fine_above) * 0.75)
                bd.reasons.append(f"{len(bear_fine_above)} {tf_name} bearish FVG(s) above")
                break

        # Gate C: protective bearish FVG above price for SL.
        # Prefer higher-TF (stronger resistance), fall back to finest entry TF.
        prot_ht = self.fvg_high.get_nearest_protective_fvg(price, "short")
        if prot_ht:
            bd.protective_fvg = prot_ht
            bd.has_protective_fvg = True
            bd.path_score += 1.0
            bd.reasons.append(
                f"Protective higher-TF bear FVG @ {prot_ht.top:.1f}-{prot_ht.bottom:.1f}"
            )
        else:
            for tracker, tf_name in self._entry_trackers():
                prot = tracker.get_nearest_protective_fvg(price, "short")
                if prot:
                    bd.protective_fvg = prot
                    bd.has_protective_fvg = True
                    bd.reasons.append(f"Protective {tf_name} bear FVG")
                    break
            else:
                bd.reasons.append("No protective bearish FVG (GATE C fail)")

        # Nested FVG confluence bonus
        if bd.protective_fvg is not None:
            bonus = self._nesting_bonus(bd.protective_fvg, "short")
            if bonus > 0:
                bd.path_score += bonus
                bd.reasons.append(f"Nested FVG confluence (short) +{bonus:.1f}")

        # Border alignment bonus — fake-out / breakdown entry signal
        if bd.protective_fvg is not None:
            align_bonus, align_reason = self._border_alignment_bonus(
                bd.protective_fvg, "short"
            )
            if align_bonus > 0:
                bd.path_score += align_bonus
                bd.reasons.append(align_reason)

        # ── TARGET SELECTION (SHORT) ──────────────────────────────────
        targets = self.liq_map.fresh_below(price, PROXIMITY_RANGE)
        _ht_bull_active = self.fvg_high.active_bullish
        viable: List[Tuple[LiquidityLevel, int]] = []
        for t in targets:
            obstacles = sum(
                1 for f in _ht_bull_active if t.price < f.midpoint < price
            )
            if obstacles <= MAX_OBSTACLES_HT:
                viable.append((t, obstacles))

        if viable:
            best, obs = viable[0]
            bd.target_level = best
            if best.weight >= LiqWeight.PDH_PDL:
                bd.target_score = 2.5
                bd.reasons.append(f"Target PDL {best.price:.1f}")
            elif best.weight >= LiqWeight.EQH_EQL:
                bd.target_score = 2.0
                bd.reasons.append(f"Target EQL {best.price:.1f}")
            else:
                bd.target_score = 1.0
                bd.reasons.append(f"Target SwL {best.price:.1f}")
            if len(viable) >= 2:
                bd.target_score += 0.5
                bd.reasons.append(f"+{len(viable)-1} more viable targets below")
            bd.target_score -= obs * 0.5
        elif bd.protective_fvg is not None:
            # Fallback: synthetic 2:1 TP anchored to the protective FVG top
            sl_dist = bd.protective_fvg.top - price
            if sl_dist > 0:
                synthetic_tp = price - sl_dist * 2.0
                bd.target_level = LiquidityLevel(
                    label="Synthetic 2:1 TP",
                    price=synthetic_tp,
                    side=LevelSide.BELOW,
                    weight=3,
                    formed_at=pd.Timestamp.now(),
                    status=LevelStatus.UNTOUCHED,
                )
                bd.target_score = 0.5
                bd.reasons.append(
                    f"Synthetic 2:1 target @ {synthetic_tp:.1f} "
                    f"(no fresh levels in {PROXIMITY_RANGE:.0f}pt range)"
                )
        else:
            bd.reasons.append("No viable target below")

        # ── MACRO ALIGNMENT (SHORT) ───────────────────────────────────
        macro = self.structure.get_macro_bias()
        if macro == StructureBias.BEARISH:
            bd.macro_score += 1.0
            bd.reasons.append("Macro (4H) bearish ✓")
        elif macro == StructureBias.BULLISH:
            # Counter-trend short: valid per philosophy — no penalty, no bonus
            bd.reasons.append("Counter-trend short (macro bullish)")

        base_bias = self.structure.get_bias("base")
        if base_bias == StructureBias.BEARISH:
            bd.macro_score += 0.5

        exhaustion = self.liq_map.upside_exhaustion()
        if exhaustion >= 7.0:
            bd.macro_score += 1.0
            bd.reasons.append(f"Upside exhausted {exhaustion:.1f}/10")
        elif exhaustion >= 4.0:
            bd.macro_score += 0.5

        # Phase 7.1 — PDH/PDL state bonus (macro-conditioned)
        pdh_pdl = self.liq_map.pdh_pdl_state()
        if (pdh_pdl["pdh_consumed"] and pdh_pdl["pdl_untouched"]
                and macro != StructureBias.BULLISH):
            bd.macro_score += 1.0
            bd.reasons.append("PDH consumed + PDL untouched → bearish liquidity skew +1.0")

        # Phase 8.2 — Discount / premium zone bonus
        self._discount_premium_bonus(bd, price)

        # ── R:R FILTER (SHORT) ────────────────────────────────────────
        if bd.target_level is not None and bd.protective_fvg is not None:
            self._apply_rr_filter(
                bd, price,
                sl_price=bd.protective_fvg.top,
                tp_price=bd.target_level.price,
            )

        # ── ATH CONTEXT (SHORT) ───────────────────────────────────────
        self._compute_ath_bonus(bd, price)

        bd.total_score = (
            bd.sweep_score + bd.structure_score
            + bd.path_score + bd.target_score + bd.macro_score
        )
        return bd
