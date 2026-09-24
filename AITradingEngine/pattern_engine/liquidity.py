"""
Liquidity & Order Flow Analysis Module.
Detects Liquidity Sweeps (stop hunts), False Breakouts (fakeouts), and Consolidation ranges.
"""
from typing import List, Tuple, Optional
from AITradingEngine.core.enums import Direction
from AITradingEngine.core.models import Candle


def detect_liquidity_sweep(
    candles: List[Candle],
    lookback: int = 25
) -> Tuple[bool, Direction, float]:
    """
    Detects Liquidity Sweep / Stop Hunt:
    - Bearish Sweep (PUT): Wick spiked above the recent swing high, but closed BELOW that high.
    - Bullish Sweep (CALL): Wick dipped below the recent swing low, but closed ABOVE that low.
    Returns: (is_sweep, suggested_reversal_direction, swept_level)
    """
    if len(candles) < lookback + 2:
        return False, Direction.NO_SIGNAL, 0.0

    recent = candles[-lookback - 1 : -1]  # Exclude current candle to find established swings
    curr = candles[-1]

    swing_high = max(c.high for c in recent)
    swing_low = min(c.low for c in recent)

    # Bullish Liquidity Sweep (Took out stops below swing_low, reversed back inside)
    if curr.low < swing_low and curr.close > swing_low:
        # Wick must be noticeable
        wick_below = swing_low - curr.low
        rng = curr.high - curr.low
        if rng > 0 and (wick_below / rng) >= 0.25:
            return True, Direction.CALL, swing_low

    # Bearish Liquidity Sweep (Took out stops above swing_high, reversed back inside)
    if curr.high > swing_high and curr.close < swing_high:
        wick_above = curr.high - swing_high
        rng = curr.high - curr.low
        if rng > 0 and (wick_above / rng) >= 0.25:
            return True, Direction.PUT, swing_high

    return False, Direction.NO_SIGNAL, 0.0


def detect_fakeout(
    candles: List[Candle],
    level: float,
    level_type: str = "resistance"
) -> Tuple[bool, Direction]:
    """
    Detects False Breakout (Fakeout):
    - A previous candle closed beyond level, but current candle sharply closed back inside.
    """
    if len(candles) < 3:
        return False, Direction.NO_SIGNAL

    prev = candles[-2]
    curr = candles[-1]

    if level_type == "resistance":
        # Broke above resistance, but current candle dumps back below
        if prev.close > level and curr.close < level:
            return True, Direction.PUT
    elif level_type == "support":
        # Broke below support, but current candle surges back above
        if prev.close < level and curr.close > level:
            return True, Direction.CALL

    return False, Direction.NO_SIGNAL


def detect_consolidation(
    candles: List[Candle],
    lookback: int = 20,
    max_range_atr_mult: float = 2.0,
    atr: float = 0.0
) -> Tuple[bool, float, float]:
    """
    Checks if market is trapped in a tight horizontal consolidation channel.
    Returns: (is_consolidating, range_high, range_low)
    """
    if len(candles) < lookback:
        return False, 0.0, 0.0

    subset = candles[-lookback:]
    range_high = max(c.high for c in subset)
    range_low = min(c.low for c in subset)
    total_range = range_high - range_low

    if atr > 0:
        if total_range <= max_range_atr_mult * atr:
            return True, range_high, range_low
    else:
        # Fallback percent of price
        avg_price = sum(c.close for c in subset) / len(subset)
        if total_range / avg_price < 0.0015:
            return True, range_high, range_low

    return False, range_high, range_low
