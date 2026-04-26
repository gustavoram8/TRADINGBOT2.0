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
from typing import List, Optional, Tuple

import pandas as pd

from indicators.structure_engine import StructureEngine, StructureBias
from indicators.liquidity_map import LiquidityMap, LiquidityLevel, LevelSide, LiqWeight
from indicators.fvg import FVGTracker, FVGType, FVGStatus, FairValueGap


# ---------------------------------------------------------------------------
# Constants (can be overridden via config/settings.py imports)
# ---------------------------------------------------------------------------
MIN_SCORE_TRADE_1 = 8.0    # First trade per day
MIN_SCORE_TRADE_2 = 12.0   # Second trade (must be exceptional)
PROXIMITY_RANGE   = 400.0  # Max points from NY AM open considered "in play"
MAX_OBSTACLES_HT  = 2      # Max intact higher-TF FVGs allowed in path to target
CHOCH_LOOKBACK    = 30     # Bars to look back for a valid CHoCH


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
    ):
        self.structure  = structure_engine
        self.liq_map    = liq_map
        self.fvg_high   = fvg_high   # Higher TF: used for path obstacles
        self.fvg_base   = fvg_base   # Base TF: used for confirmations & protective FVG

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
        # Higher-TF bearish FVGs above price = obstacles to upside targets
        ht_bear_above = [
            f for f in self.fvg_high.all_fvgs
            if f.fvg_type == FVGType.BEARISH and f.is_active and f.bottom >= price
        ]
        n_obstacles = len(ht_bear_above)

        if n_obstacles == 0:
            bd.path_score += 3.0
            bd.reasons.append("No higher-TF bearish FVGs above (clear path)")
        elif n_obstacles == 1:
            bd.path_score += 1.5
            bd.reasons.append("1 higher-TF bearish FVG above (partial obstacle)")
        elif n_obstacles == 2:
            bd.path_score += 0.5
            bd.reasons.append("2 higher-TF bearish FVGs above (tight path)")
        else:
            bd.path_score -= 1.0
            bd.reasons.append(f"{n_obstacles} higher-TF bearish FVGs above (PENALTY)")

        # Recently broken higher-TF bearish FVGs → path opening
        ht_bear_broken = [
            f for f in self.fvg_high.all_fvgs
            if f.fvg_type == FVGType.BEARISH and f.status == FVGStatus.BROKEN
        ]
        if ht_bear_broken:
            bd.path_score += min(1.5, len(ht_bear_broken) * 0.75)
            bd.reasons.append(f"{len(ht_bear_broken)} higher-TF bear FVG(s) broken")

        # Base-TF bullish FVGs near price → potential protective FVG
        bull_base_below = [
            f for f in self.fvg_base.all_fvgs
            if f.fvg_type == FVGType.BULLISH and f.is_active
            and f.top <= price and price - f.top <= 150
        ]
        bull_base_below.sort(key=lambda f: price - f.top)

        if bull_base_below:
            bd.protective_fvg = bull_base_below[0]
            bd.has_protective_fvg = True
            bd.path_score += 1.0
            bd.reasons.append(f"Protective bull FVG @ {bull_base_below[0].top:.1f}-{bull_base_below[0].bottom:.1f}")
        else:
            # Fallback: higher-TF bullish FVG below price
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
        # Higher-TF bullish FVGs below price that are still ACTIVE = obstacles
        ht_bull_below = [
            f for f in self.fvg_high.all_fvgs
            if f.fvg_type == FVGType.BULLISH and f.is_active and f.top <= price
        ]
        ht_bull_below.sort(key=lambda f: price - f.top)

        # "Key" 1H bull FVGs just broken = path opening (most important signal)
        ht_bull_broken = [
            f for f in self.fvg_high.all_fvgs
            if f.fvg_type == FVGType.BULLISH and f.status == FVGStatus.BROKEN
        ]
        if ht_bull_broken:
            bd.path_score += 3.0
            bd.reasons.append(f"{len(ht_bull_broken)} key higher-TF bull FVG(s) BROKEN")

        # Immediate path: intact higher-TF bull FVGs within 100 pts below price
        immediate = [f for f in ht_bull_below if price - f.top <= 100]
        if len(immediate) == 0:
            bd.path_score += 2.0
            bd.reasons.append("No higher-TF bull FVG in immediate 100-pt path")
        elif len(immediate) == 1:
            bd.path_score += 0.5
            bd.reasons.append("1 bull FVG in immediate path (manageable)")
        else:
            bd.path_score -= 1.0
            bd.reasons.append(f"{len(immediate)} bull FVGs blocking immediate path (PENALTY)")

        # Base-TF bearish FVGs above price = downward intent confirmation
        bear_base_above = [
            f for f in self.fvg_base.all_fvgs
            if f.fvg_type == FVGType.BEARISH and f.is_active and f.bottom >= price
        ]
        if bear_base_above:
            bd.path_score += min(2.0, len(bear_base_above) * 0.75)
            bd.reasons.append(f"{len(bear_base_above)} base-TF bearish FVG(s) above")

        # ── GATE C: protective bearish FVG for SL ─────────────────────
        prot_ht = self.fvg_high.get_nearest_protective_fvg(price, "short")
        if prot_ht:
            bd.protective_fvg = prot_ht
            bd.has_protective_fvg = True
            bd.path_score += 1.0
            bd.reasons.append(f"Protective higher-TF bear FVG @ {prot_ht.top:.1f}-{prot_ht.bottom:.1f}")
        else:
            prot_base = self.fvg_base.get_nearest_protective_fvg(price, "short")
            if prot_base:
                bd.protective_fvg = prot_base
                bd.has_protective_fvg = True
                bd.reasons.append(f"Protective base-TF bear FVG")
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
