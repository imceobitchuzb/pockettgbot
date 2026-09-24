"""
AITradingEngine Volatility Module.
Implements Average True Range (ATR), Bollinger Bands, Bandwidth Squeeze, and Volatility Regimes.
"""
import math
from typing import List, Dict, Any, Tuple, Union


class BollingerBandsResult(dict):
    """Holds Bollinger Bands results accessible via attributes or dictionary keys."""
    def __init__(self, middle: float, upper: float, lower: float, bandwidth: float, percent_b: float, is_squeeze: bool = False):
        super().__init__(
            middle=middle,
            upper=upper,
            lower=lower,
            bandwidth=bandwidth,
            percent_b=percent_b,
            is_squeeze=is_squeeze
        )
        self.middle = middle
        self.upper = upper
        self.lower = lower
        self.bandwidth = bandwidth
        self.percent_b = percent_b
        self.is_squeeze = is_squeeze


def calc_atr(
    highs: Union[List[float], List[Any]],
    lows: Optional[List[float]] = None,
    closes: Optional[List[float]] = None,
    period: int = 14
) -> float:
    if highs and hasattr(highs[0], "high"):
        candles = highs
        h_vals = [c.high for c in candles]
        l_vals = [c.low for c in candles]
        c_vals = [c.close for c in candles]
    else:
        h_vals = highs
        l_vals = lows or []
        c_vals = closes or []

    n = len(c_vals)
    if n < 2:
        return 0.0001
    tr_list = []
    for i in range(1, n):
        tr = max(h_vals[i] - l_vals[i], abs(h_vals[i] - c_vals[i - 1]), abs(l_vals[i] - c_vals[i - 1]))
        tr_list.append(tr)
    slice_tr = tr_list[-period:]
    return round(sum(slice_tr) / len(slice_tr), 6) if slice_tr else 0.0001


def calc_bollinger_bands(
    closes: Union[List[float], List[Any]],
    period: int = 20,
    std_dev: float = 2.0
) -> BollingerBandsResult:
    if closes and hasattr(closes[0], "close"):
        c_vals = [c.close for c in closes]
    else:
        c_vals = closes or []

    n = len(c_vals)
    if n < period:
        last = c_vals[-1] if c_vals else 0.0
        return BollingerBandsResult(last, last, last, 0.0, 0.5, False)

    slice_vals = c_vals[-period:]
    mid = sum(slice_vals) / period
    variance = sum((x - mid) ** 2 for x in slice_vals) / period
    std = math.sqrt(variance)

    upper = mid + std_dev * std
    lower = mid - std_dev * std
    bandwidth = (upper - lower) / mid if mid > 0 else 0.0

    cur_p = c_vals[-1]
    denom = upper - lower
    percent_b = ((cur_p - lower) / denom) if denom > 0 else 0.5
    is_squeeze = bandwidth < 0.0015

    return BollingerBandsResult(
        middle=round(mid, 5),
        upper=round(upper, 5),
        lower=round(lower, 5),
        bandwidth=round(bandwidth, 5),
        percent_b=round(percent_b, 3),
        is_squeeze=is_squeeze
    )


calculate_atr = calc_atr
calculate_bollinger_bands = calc_bollinger_bands


def detect_volatility_regime(current_atr: float, baseline_atr: float, bb_bandwidth: float) -> Dict[str, Any]:
    ratio = (current_atr / baseline_atr) if baseline_atr > 0 else 1.0
    is_squeeze = bb_bandwidth < 0.0015 or ratio < 0.65

    if ratio > 2.2:
        regime = "EXTREME_VOLATILITY"
    elif ratio > 1.3:
        regime = "HIGH_VOLATILITY"
    elif ratio < 0.65:
        regime = "LOW_VOLATILITY"
    else:
        regime = "NORMAL_VOLATILITY"

    return {
        "regime": regime,
        "is_squeeze": is_squeeze,
        "atr_expansion_ratio": round(ratio, 2)
    }
