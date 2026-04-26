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
from indicators.liquidity_map import LiquidityMap, LiquidityLevel, LevelSide, LiqWeight
from indicators.fvg import FVGTracker, FVGType, FVGStatus, FairValueGap
from config.settings import (
    SCORER_MIN_SCORE_TRADE_1 as MIN_SCORE_TRADE_1,
    SCORER_MIN_SCORE_TRADE_2 as MIN_SCORE_TRADE_2,
    SCORER_PROXIMITY_RANGE_POINTS as PROXIMITY_RANGE,
    SCORER_MAX_PATH_OBSTACLES as MAX_OBSTACLES_HT,
    SCORER_CHOCH_LOOKBACK_BARS as CHOCH_LOOKBACK,
)


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

    # Selected levels (filled in if gates pass)
    target_level:    Optional[LiquidityLevel] = None
    protective_fvg:  Optional[FairValueGap]   = None

    reasons: List[str] = field(default_factory=list)

    @property
    def gates_passed(self) -> bool:
        return self.has_sweep and self.has_choch and self.has_protective_fvg

    def log_str(self) -> str:
        g = f"[S:{int(self.has_sweep)} C:{int(self.has_choch)} F:{int(self.has_protective_fvg)}]"
        return (
            f"{self.direction.upper()} {g} total={self.total_score:.1f} "
            f"(swp={self.sweep_score:.1f} str={self.structure_score:.1f} "
            f"path={self.path_score:.1f} tgt={self.target_score:.1f} "
            f"mac={self.macro_score:.1f})"
        )


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

    def set_bar(self, bar_idx: int):
        """Call once per bar so significance scores use correct age."""
        self._current_bar = bar_idx

    # Timeframe weights for significance_score()
    _TF_WEIGHT = {"4h": 4.0, "1h": 3.0, "15m": 2.0, "5m": 1.0, "base": 3.0}

    def _sig(self, fvg, tf: str = "base") -> float:
        """Shorthand: significance score for an FVG at the current bar."""
        return fvg.significance_score(self._current_bar, self._TF_WEIGHT.get(tf, 1.0))

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

        candidates = [
            bd for bd in (long_bd, short_bd)
            if bd.gates_passed and bd.total_score >= threshold
        ]
        return max(candidates, key=lambda bd: bd.total_score) if candidates else None

    def score_both(
        self, price: float
    ) -> Tuple[ScoreBreakdown, ScoreBreakdown]:
        return self._score_long(price), self._score_short(price)

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

        # ── GATE B: CHoCH bullish (close-confirmed) ───────────────────
        if self.structure.had_confirmation_choch("bullish", CHOCH_LOOKBACK):
            bd.has_choch = True
            bd.structure_score = 3.0
            bd.reasons.append("CHoCH bullish confirmed")
            # Multi-TF bonus
            confirmed_tfs = [
                tf for tf in ("base", "15m", "5m", "1m")
                if tf in self.structure.trackers
                and self.structure.trackers[tf].had_choch_recently("bullish", CHOCH_LOOKBACK)
            ]
            if len(confirmed_tfs) >= 2:
                bd.structure_score += 1.0
                bd.reasons.append(f"CHoCH on {confirmed_tfs}")

        # ── FVG PATH (LONG) ───────────────────────────────────────────
        # Higher-TF bearish FVGs above price = obstacles (weighted by significance)
        ht_bear_above = [
            f for f in self.fvg_high.all_fvgs
            if f.fvg_type == FVGType.BEARISH and f.is_active and f.bottom >= price
        ]
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

        # Recently broken higher-TF bearish FVGs → path opening
        # Older/more significant broken FVG = bigger confirmation
        ht_bear_broken = [
            f for f in self.fvg_high.all_fvgs
            if f.fvg_type == FVGType.BEARISH and f.status == FVGStatus.BROKEN
        ]
        if ht_bear_broken:
            # Use the most significant broken FVG as the signal strength
            max_broken_sig = max(
                fvg.significance_score(self._current_bar, self._TF_WEIGHT.get("4h", 4.0))
                for fvg in ht_bear_broken
            )
            broken_bonus = min(2.0, 0.5 + max_broken_sig * 0.3)
            bd.path_score += broken_bonus
            bd.reasons.append(
                f"{len(ht_bear_broken)} higher-TF bear FVG(s) broken "
                f"(max_sig={max_broken_sig:.1f} → +{broken_bonus:.1f})"
            )

        # Gate C: protective bullish FVG below price for SL.
        # Prefer finest TF (tightest SL), fall back to higher-TF.
        for tracker, tf_name in self._entry_trackers():
            candidates = [
                f for f in tracker.all_fvgs
                if f.fvg_type == FVGType.BULLISH and f.is_active
                and f.top <= price and price - f.top <= 150
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

        # ── TARGET SELECTION (LONG) ───────────────────────────────────
        targets = self.liq_map.fresh_above(price, PROXIMITY_RANGE)
        viable: List[Tuple[LiquidityLevel, int]] = []
        for t in targets:
            # Count intact higher-TF bear FVGs between price and target
            obstacles = sum(
                1 for f in self.fvg_high.all_fvgs
                if f.fvg_type == FVGType.BEARISH and f.is_active
                and price < f.midpoint < t.price
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

        # ── GATE B: CHoCH bearish (close-confirmed) ───────────────────
        if self.structure.had_confirmation_choch("bearish", CHOCH_LOOKBACK):
            bd.has_choch = True
            bd.structure_score = 3.0
            bd.reasons.append("CHoCH bearish confirmed")
            confirmed_tfs = [
                tf for tf in ("base", "15m", "5m", "1m")
                if tf in self.structure.trackers
                and self.structure.trackers[tf].had_choch_recently("bearish", CHOCH_LOOKBACK)
            ]
            if len(confirmed_tfs) >= 2:
                bd.structure_score += 1.0
                bd.reasons.append(f"CHoCH on {confirmed_tfs}")

        # ── FVG PATH (SHORT) ──────────────────────────────────────────
        # Higher-TF bullish FVGs below price = obstacles (weighted by significance)
        ht_bull_below = [
            f for f in self.fvg_high.all_fvgs
            if f.fvg_type == FVGType.BULLISH and f.is_active and f.top <= price
        ]
        ht_bull_below.sort(key=lambda f: price - f.top)

        # "Key" bull FVGs just broken: more significant broken FVG = stronger signal
        ht_bull_broken = [
            f for f in self.fvg_high.all_fvgs
            if f.fvg_type == FVGType.BULLISH and f.status == FVGStatus.BROKEN
        ]
        if ht_bull_broken:
            max_broken_sig = max(
                fvg.significance_score(self._current_bar, self._TF_WEIGHT.get("4h", 4.0))
                for fvg in ht_bull_broken
            )
            broken_bonus = min(4.0, 1.5 + max_broken_sig * 0.5)
            bd.path_score += broken_bonus
            bd.reasons.append(
                f"{len(ht_bull_broken)} key higher-TF bull FVG(s) BROKEN "
                f"(max_sig={max_broken_sig:.1f} → +{broken_bonus:.1f})"
            )

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
            bear_fine_above = [
                f for f in tracker.all_fvgs
                if f.fvg_type == FVGType.BEARISH and f.is_active and f.bottom >= price
            ]
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

        # ── TARGET SELECTION (SHORT) ──────────────────────────────────
        targets = self.liq_map.fresh_below(price, PROXIMITY_RANGE)
        viable: List[Tuple[LiquidityLevel, int]] = []
        for t in targets:
            # Count intact higher-TF bull FVGs between price and target
            obstacles = sum(
                1 for f in self.fvg_high.all_fvgs
                if f.fvg_type == FVGType.BULLISH and f.is_active
                and t.price < f.midpoint < price
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

        bd.total_score = (
            bd.sweep_score + bd.structure_score
            + bd.path_score + bd.target_score + bd.macro_score
        )
        return bd
