"""
Structure Engine — Dow Theory market structure tracking per timeframe.

Detects HH/HL (bullish) and LH/LL (bearish) sequences.
CHoCH (Change of Character) and BOS (Break of Structure) are ONLY
confirmed on candle CLOSE — wick-only breaks are ignored.

Usage:
    engine = StructureEngine(["4h", "base"])
    engine.update("base", open_, high, low, close, timestamp)
    bias = engine.get_bias("base")
    choch = engine.had_confirmation_choch("bearish", lookback_bars=30)
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import pandas as pd


class StructureBias(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class StructureEvent(Enum):
    HH = "higher_high"
    HL = "higher_low"
    LH = "lower_high"
    LL = "lower_low"
    CHOCH_BEARISH = "choch_bearish"   # Uptrend HL broken on close
    CHOCH_BULLISH = "choch_bullish"   # Downtrend LH broken on close
    BOS_BULLISH = "bos_bullish"       # Confirmed bullish continuation
    BOS_BEARISH = "bos_bearish"       # Confirmed bearish continuation


@dataclass
class SwingPoint:
    price: float
    timestamp: pd.Timestamp
    bar_idx: int
    is_high: bool


@dataclass
class StructureSignal:
    event: StructureEvent
    price: float
    timestamp: pd.Timestamp
    bar_idx: int
    timeframe: str
    broken_level: float


class TFStructureTracker:
    """
    Tracks Dow theory swing structure for ONE timeframe.
    All CHoCH/BOS signals require a candle CLOSE beyond the structural level.
    """

    def __init__(self, timeframe: str, swing_order: int = 3):
        self.timeframe = timeframe
        self.swing_order = swing_order

        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.bias: StructureBias = StructureBias.NEUTRAL
        self.signals: List[StructureSignal] = []

        self._buf: List[dict] = []
        self._bar_idx: int = 0

    def update(
        self,
        open_: float, high: float, low: float, close: float,
        timestamp: pd.Timestamp,
    ) -> List[StructureSignal]:
        """Feed one closed candle. Returns newly emitted signals."""
        self._bar_idx += 1
        self._buf.append({
            "o": open_, "h": high, "l": low, "c": close,
            "ts": timestamp, "idx": self._bar_idx,
        })
        if len(self._buf) > 150:
            self._buf.pop(0)

        new_sigs: List[StructureSignal] = []

        order = self.swing_order
        if len(self._buf) < order * 2 + 1:
            return new_sigs

        # Confirm swings at the candle that is `order` bars ago (fully confirmed)
        self._detect_swing_at_pivot(order, new_sigs)

        # Check for CHoCH / BOS on the current closed candle
        self._check_structure_break(close, timestamp, new_sigs)

        self.signals.extend(new_sigs)
        if len(self.signals) > 100:
            self.signals = self.signals[-100:]

        return new_sigs

    # -------------------------------------------------------------------------
    def _detect_swing_at_pivot(self, order: int, new_sigs: List[StructureSignal]):
        buf = self._buf
        pivot_i = len(buf) - order - 1

        if pivot_i < order:
            return

        pivot = buf[pivot_i]

        # --- Swing High ---
        is_sh = (
            all(buf[pivot_i - k]["h"] <= pivot["h"] for k in range(1, order + 1) if pivot_i - k >= 0)
            and all(buf[pivot_i + k]["h"] <= pivot["h"] for k in range(1, order + 1))
        )
        if is_sh:
            sp = SwingPoint(pivot["h"], pivot["ts"], pivot["idx"], is_high=True)
            if not self.swing_highs or abs(self.swing_highs[-1].price - sp.price) > 0.5:
                self.swing_highs.append(sp)
                if len(self.swing_highs) >= 2:
                    prev = self.swing_highs[-2]
                    evt = StructureEvent.HH if sp.price > prev.price else StructureEvent.LH
                    new_sigs.append(StructureSignal(evt, sp.price, sp.timestamp,
                                                    sp.bar_idx, self.timeframe, prev.price))

        # --- Swing Low ---
        is_sl = (
            all(buf[pivot_i - k]["l"] >= pivot["l"] for k in range(1, order + 1) if pivot_i - k >= 0)
            and all(buf[pivot_i + k]["l"] >= pivot["l"] for k in range(1, order + 1))
        )
        if is_sl:
            sp = SwingPoint(pivot["l"], pivot["ts"], pivot["idx"], is_high=False)
            if not self.swing_lows or abs(self.swing_lows[-1].price - sp.price) > 0.5:
                self.swing_lows.append(sp)
                if len(self.swing_lows) >= 2:
                    prev = self.swing_lows[-2]
                    evt = StructureEvent.HL if sp.price > prev.price else StructureEvent.LL
                    new_sigs.append(StructureSignal(evt, sp.price, sp.timestamp,
                                                    sp.bar_idx, self.timeframe, prev.price))

        self._recompute_bias()

    def _recompute_bias(self):
        if len(self.swing_highs) < 2 or len(self.swing_lows) < 2:
            return
        h1, h2 = self.swing_highs[-2], self.swing_highs[-1]
        l1, l2 = self.swing_lows[-2], self.swing_lows[-1]
        hh = h2.price > h1.price
        hl = l2.price > l1.price
        lh = h2.price < h1.price
        ll = l2.price < l1.price
        if hh and hl:
            self.bias = StructureBias.BULLISH
        elif lh and ll:
            self.bias = StructureBias.BEARISH

    def _check_structure_break(
        self, close: float, timestamp: pd.Timestamp, new_sigs: List[StructureSignal]
    ):
        """Emit CHoCH when CLOSE breaks the last protective structural level."""
        if self.bias == StructureBias.BULLISH and self.swing_lows:
            last_hl = self.swing_lows[-1].price
            if close < last_hl:
                sig = StructureSignal(
                    StructureEvent.CHOCH_BEARISH, close, timestamp,
                    self._bar_idx, self.timeframe, last_hl,
                )
                new_sigs.append(sig)
                self.bias = StructureBias.BEARISH

        elif self.bias == StructureBias.BEARISH and self.swing_highs:
            last_lh = self.swing_highs[-1].price
            if close > last_lh:
                sig = StructureSignal(
                    StructureEvent.CHOCH_BULLISH, close, timestamp,
                    self._bar_idx, self.timeframe, last_lh,
                )
                new_sigs.append(sig)
                self.bias = StructureBias.BULLISH

    # -------------------------------------------------------------------------
    def had_choch_recently(
        self, direction: str, lookback_bars: int = 30
    ) -> Optional[StructureSignal]:
        """
        Return the most recent CHoCH signal matching `direction` within
        the last `lookback_bars` bars of this TF. None if not found.
        direction: "bullish" or "bearish"
        """
        target = (
            StructureEvent.CHOCH_BULLISH
            if direction == "bullish"
            else StructureEvent.CHOCH_BEARISH
        )
        threshold = self._bar_idx - lookback_bars
        for sig in reversed(self.signals):
            if sig.event == target and sig.bar_idx >= threshold:
                return sig
        return None

    def get_last_swing_high(self) -> Optional[SwingPoint]:
        return self.swing_highs[-1] if self.swing_highs else None

    def get_last_swing_low(self) -> Optional[SwingPoint]:
        return self.swing_lows[-1] if self.swing_lows else None


# =============================================================================
# Multi-TF facade
# =============================================================================
class StructureEngine:
    """
    Maintains one TFStructureTracker per timeframe.
    Supports arbitrary timeframe labels — strategy passes in whatever TFs it has.
    """

    # Swing order (bars each side to confirm a swing) per TF
    _TF_ORDER: Dict[str, int] = {
        "4h": 3, "1h": 3, "15m": 3, "5m": 2, "1m": 2, "base": 3,
    }

    def __init__(self, timeframes: List[str]):
        self.trackers: Dict[str, TFStructureTracker] = {
            tf: TFStructureTracker(tf, self._TF_ORDER.get(tf, 3))
            for tf in timeframes
        }

    def update(
        self, timeframe: str,
        open_: float, high: float, low: float, close: float,
        timestamp: pd.Timestamp,
    ) -> List[StructureSignal]:
        if timeframe not in self.trackers:
            return []
        return self.trackers[timeframe].update(open_, high, low, close, timestamp)

    def get_bias(self, timeframe: str) -> StructureBias:
        if timeframe not in self.trackers:
            return StructureBias.NEUTRAL
        return self.trackers[timeframe].bias

    def get_macro_bias(self) -> StructureBias:
        """Use the highest available TF as macro bias."""
        for tf in ("4h", "1h", "base"):
            if tf in self.trackers:
                return self.trackers[tf].bias
        return StructureBias.NEUTRAL

    def had_confirmation_choch(
        self,
        direction: str,
        lookback_bars: int = 30,
        confirmation_tfs: Optional[List[str]] = None,
    ) -> bool:
        """
        True if ANY of the confirmation TFs had a CHoCH in the given direction
        within the last `lookback_bars` bars of that TF.
        Defaults to checking "base" (which is the entry-TF in single-feed setup).
        """
        tfs = confirmation_tfs or ["base", "15m", "5m", "1m"]
        for tf in tfs:
            if tf in self.trackers:
                if self.trackers[tf].had_choch_recently(direction, lookback_bars):
                    return True
        return False

    def get_latest_choch(
        self,
        direction: str,
        lookback_bars: int = 30,
        confirmation_tfs: Optional[List[str]] = None,
    ) -> Optional[StructureSignal]:
        """Return the most recent CHoCH signal across confirmation TFs."""
        tfs = confirmation_tfs or ["base", "15m", "5m", "1m"]
        candidates: List[StructureSignal] = []
        for tf in tfs:
            if tf in self.trackers:
                sig = self.trackers[tf].had_choch_recently(direction, lookback_bars)
                if sig:
                    candidates.append(sig)
        return max(candidates, key=lambda s: s.bar_idx) if candidates else None
