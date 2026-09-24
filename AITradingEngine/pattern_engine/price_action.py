"""
Price Action Pattern Detection Module.
Detects Support/Resistance zones, Pin Bars (Rejection Wicks), Engulfing, and Inside Bars.
All calculations are strictly point-in-time on completed candles.
"""
from typing import List, Dict, Tuple, Optional
from AITradingEngine.core.enums import Direction
from AITradingEngine.core.models import Candle


def detect_sr_levels(
    candles: List[Candle],
    lookback: int = 60,
    cluster_tolerance: float = 0.0003,
    min_touches: int = 2
) -> Dict[str, List[float]]:
    """
    Finds Support and Resistance levels by clustering swing highs and swing lows.
    Returns: {"support": [level1, ...], "resistance": [level1, ...]}
    """
    if len(candles) < 10:
        return {"support": [], "resistance": []}

    subset = candles[-lookback:] if len(candles) > lookback else candles
    highs = []
    lows = []

    # Swing detection (local extrema with window of 3)
    for i in range(2, len(subset) - 2):
        c_prev2 = subset[i - 2]
        c_prev1 = subset[i - 1]
        c = subset[i]
        c_next1 = subset[i + 1]
        c_next2 = subset[i + 2]

        # Swing High
        if c.high > c_prev1.high and c.high > c_prev2.high and c.high > c_next1.high and c.high > c_next2.high:
            highs.append(c.high)

        # Swing Low
        if c.low < c_prev1.low and c.low < c_prev2.low and c.low < c_next1.low and c.low < c_next2.low:
            lows.append(c.low)

    def cluster_levels(raw_levels: List[float]) -> List[float]:
        if not raw_levels:
            return []
        sorted_lvls = sorted(raw_levels)
        clusters: List[List[float]] = []

        for lvl in sorted_lvls:
            added = False
            for group in clusters:
                avg = sum(group) / len(group)
                if abs(lvl - avg) / (avg if avg > 0 else 1.0) <= cluster_tolerance:
                    group.append(lvl)
                    added = True
                    break
            if not added:
                clusters.append([lvl])

        # Keep clusters with at least min_touches
        result = []
        for group in clusters:
            if len(group) >= min_touches:
                result.append(round(sum(group) / len(group), 5))
        return result

    return {
        "resistance": cluster_levels(highs),
        "support": cluster_levels(lows)
    }


def detect_pin_bar(candle: Candle, atr: float = 0.0) -> Tuple[bool, Direction]:
    """
    Detects rejection wick / pin bar.
    - Bullish Pin Bar (CALL): long lower shadow >= 60% of total range, body <= 30% of total range.
    - Bearish Pin Bar (PUT): long upper shadow >= 60% of total range, body <= 30% of total range.
    """
    rng = candle.high - candle.low
    if rng <= 0:
        return False, Direction.NO_SIGNAL

    # If ATR provided, check minimum significance
    if atr > 0 and rng < 0.4 * atr:
        return False, Direction.NO_SIGNAL

    body = abs(candle.close - candle.open)
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low

    body_ratio = body / rng
    upper_ratio = upper_wick / rng
    lower_ratio = lower_wick / rng

    # Bullish rejection (Buyers stepped in strongly from below)
    if lower_ratio >= 0.58 and body_ratio <= 0.32 and upper_ratio <= 0.20:
        return True, Direction.CALL

    # Bearish rejection (Sellers stepped in strongly from above)
    if upper_ratio >= 0.58 and body_ratio <= 0.32 and lower_ratio <= 0.20:
        return True, Direction.PUT

    return False, Direction.NO_SIGNAL


def detect_engulfing(prev: Candle, curr: Candle) -> Tuple[bool, Direction]:
    """
    Detects classic Bullish or Bearish Engulfing pattern.
    """
    prev_body = prev.close - prev.open
    curr_body = curr.close - curr.open

    # Bullish engulfing: previous was red, current is green and engulfs body
    if prev_body < 0 and curr_body > 0:
        if curr.open <= prev.close and curr.close >= prev.open and abs(curr_body) > abs(prev_body) * 1.1:
            return True, Direction.CALL

    # Bearish engulfing: previous was green, current is red and engulfs body
    if prev_body > 0 and curr_body < 0:
        if curr.open >= prev.close and curr.close <= prev.open and abs(curr_body) > abs(prev_body) * 1.1:
            return True, Direction.PUT

    return False, Direction.NO_SIGNAL


def detect_inside_bar(prev: Candle, curr: Candle) -> bool:
    """
    Checks if current candle is completely inside previous candle's range.
    """
    return curr.high <= prev.high and curr.low >= prev.low


def check_sr_rejection(
    candle: Candle,
    sr_levels: Dict[str, List[float]],
    atr: float
) -> Tuple[bool, Direction, float]:
    """
    Checks if current candle rejects an established support or resistance level.
    Returns: (is_rejection, Direction, rejected_level)
    """
    tolerance = 0.5 * atr if atr > 0 else 0.0003
    is_pin, pin_dir = detect_pin_bar(candle, atr)

    # Bullish rejection at Support
    if pin_dir == Direction.CALL or candle.low < candle.close:
        for sup in sr_levels.get("support", []):
            if abs(candle.low - sup) <= tolerance and candle.close > sup:
                return True, Direction.CALL, sup

    # Bearish rejection at Resistance
    if pin_dir == Direction.PUT or candle.high > candle.close:
        for res in sr_levels.get("resistance", []):
            if abs(candle.high - res) <= tolerance and candle.close < res:
                return True, Direction.PUT, res

    return False, Direction.NO_SIGNAL, 0.0
