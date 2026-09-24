"""
Market Noise & Choppiness Filter.
Calculates Choppiness Index (CI) and Kaufman Efficiency Ratio (ER) to detect chaotic, untradable markets.
"""
import math
from typing import List, Dict, Any
from AITradingEngine.core.models import Candle


def calculate_choppiness_index(candles: List[Candle], period: int = 14) -> float:
    """
    Choppiness Index (CI):
    CI = 100 * log10( Sum(ATR_1, period) / (HighestHigh(period) - LowestLow(period)) ) / log10(period)
    Values > 61.8 indicate extreme chop / lack of direction.
    Values < 38.2 indicate strong directional trending.
    """
    if len(candles) < period + 1:
        return 50.0

    subset = candles[-period:]
    true_ranges = []
    for i in range(1, len(subset)):
        h = subset[i].high
        l = subset[i].low
        prev_c = subset[i - 1].close
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        true_ranges.append(tr)

    sum_tr = sum(true_ranges)
    highest_high = max(c.high for c in subset)
    lowest_low = min(c.low for c in subset)
    price_range = highest_high - lowest_low

    if price_range <= 0 or sum_tr <= 0:
        return 65.0  # Safe default to choppy if no range

    try:
        ci = 100.0 * (math.log10(sum_tr / price_range) / math.log10(period))
        return min(max(ci, 0.0), 100.0)
    except (ValueError, ZeroDivisionError):
        return 50.0


def calculate_efficiency_ratio(candles: List[Candle], period: int = 14) -> float:
    """
    Kaufman Efficiency Ratio (ER):
    ER = Total Directional Movement / Sum of individual absolute step changes
    1.0 = Pure straight trend.
    0.0 - 0.20 = High noise / chop / zigzag.
    """
    if len(candles) < period + 1:
        return 0.5

    subset = candles[-period - 1:]
    total_change = abs(subset[-1].close - subset[0].close)

    individual_changes = sum(abs(subset[i].close - subset[i - 1].close) for i in range(1, len(subset)))
    if individual_changes == 0:
        return 0.0

    return total_change / individual_changes


def evaluate_noise(candles: List[Candle], period: int = 14) -> Dict[str, Any]:
    """
    Comprehensive Noise evaluation.
    Flags is_noisy=True if Choppiness Index > 61.8 or Kaufman ER < 0.22.
    """
    ci = calculate_choppiness_index(candles, period)
    er = calculate_efficiency_ratio(candles, period)

    is_choppy = ci > 61.8
    is_inefficient = er < 0.22
    is_noisy = is_choppy or is_inefficient

    return {
        "is_noisy": is_noisy,
        "choppiness_index": round(ci, 2),
        "efficiency_ratio": round(er, 4),
        "regime_status": "CHOPPY" if is_choppy else ("NOISY" if is_inefficient else "CLEAN")
    }
