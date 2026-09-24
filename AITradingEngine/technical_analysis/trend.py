"""
AITradingEngine Trend Analysis Module.
Implements EMA, SMA, MACD, ADX (Welles Wilder), and Price Structure (HH, HL, LH, LL).
"""
import math
from typing import List, Dict, Any, Tuple, NamedTuple, Union


class ADXResult(tuple):
    def __new__(cls, adx: float, plus_di: float, minus_di: float, is_trending: bool = False):
        obj = tuple.__new__(cls, (adx, plus_di, minus_di))
        obj.adx = adx
        obj.plus_di = plus_di
        obj.minus_di = minus_di
        obj.is_trending = is_trending
        return obj

    def __getitem__(self, item):
        if isinstance(item, str):
            return getattr(self, item)
        return tuple.__getitem__(self, item)



def calc_sma(values: List[float], period: int) -> List[float]:
    if len(values) < period:
        return values.copy()
    sma = []
    for i in range(len(values)):
        if i < period - 1:
            sma.append(values[i])
        else:
            sma.append(sum(values[i - period + 1 : i + 1]) / period)
    return sma


def calc_ema(values: List[float], period: int) -> List[float]:
    if len(values) < period:
        return values.copy()
    ema = [0.0] * len(values)
    multiplier = 2.0 / (period + 1.0)
    sma_init = sum(values[:period]) / period
    for i in range(period):
        ema[i] = values[i]
    ema[period - 1] = sma_init
    for i in range(period, len(values)):
        ema[i] = (values[i] - ema[i - 1]) * multiplier + ema[i - 1]
    return ema


def calc_macd(closes: List[float], fast: int = 12, slow: int = 26, signal_period: int = 9) -> Dict[str, List[float]]:
    n = len(closes)
    if n < slow:
        return {"macd": [0.0] * n, "signal": [0.0] * n, "hist": [0.0] * n}
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(n)]
    signal_line = calc_ema(macd_line, signal_period)
    hist = [macd_line[i] - signal_line[i] for i in range(n)]
    return {
        "macd": [round(v, 6) for v in macd_line],
        "signal": [round(v, 6) for v in signal_line],
        "hist": [round(v, 6) for v in hist]
    }


def calc_adx(
    highs: Union[List[float], List[Any]],
    lows: Optional[List[float]] = None,
    closes: Optional[List[float]] = None,
    period: int = 14
) -> Dict[str, Any]:
    """Calculates Wilder's Directional Movement Index."""
    # Support passing list of Candle
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
    if n <= period * 2:
        return {"adx": 20.0, "plus_di": 20.0, "minus_di": 20.0, "is_trending": False}

    tr = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n

    for i in range(1, n):
        h_diff = h_vals[i] - h_vals[i - 1]
        l_diff = l_vals[i - 1] - l_vals[i]

        plus_dm[i] = h_diff if (h_diff > l_diff and h_diff > 0) else 0.0
        minus_dm[i] = l_diff if (l_diff > h_diff and l_diff > 0) else 0.0

        tr[i] = max(
            h_vals[i] - l_vals[i],
            abs(h_vals[i] - c_vals[i - 1]),
            abs(l_vals[i] - c_vals[i - 1])
        )

    smoothed_tr = sum(tr[1: period + 1])
    smoothed_pdm = sum(plus_dm[1: period + 1])
    smoothed_mdm = sum(minus_dm[1: period + 1])

    dx_list = []
    adx = 20.0

    for i in range(period + 1, n):
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + tr[i]
        smoothed_pdm = smoothed_pdm - (smoothed_pdm / period) + plus_dm[i]
        smoothed_mdm = smoothed_mdm - (smoothed_mdm / period) + minus_dm[i]

        pdi = (smoothed_pdm / smoothed_tr * 100) if smoothed_tr > 0 else 0
        mdi = (smoothed_mdm / smoothed_tr * 100) if smoothed_tr > 0 else 0

        denom = pdi + mdi
        dx = (abs(pdi - mdi) / denom * 100) if denom > 0 else 0
        dx_list.append((dx, pdi, mdi))

    if len(dx_list) >= period:
        adx = sum(d[0] for d in dx_list[-period:]) / period
        last_pdi = dx_list[-1][1]
        last_mdi = dx_list[-1][2]
    else:
        last_pdi = 20.0
        last_mdi = 20.0

    return {
        "adx": round(adx, 2),
        "plus_di": round(last_pdi, 2),
        "minus_di": round(last_mdi, 2),
        "is_trending": adx >= 25.0
    }


def calculate_adx(
    highs: Union[List[float], List[Any]],
    lows: Optional[List[float]] = None,
    closes: Optional[List[float]] = None,
    period: int = 14
) -> Tuple[float, float, float]:
    """Returns (adx, plus_di, minus_di) as namedtuple for unpacking."""
    res = calc_adx(highs, lows, closes, period)
    return ADXResult(res["adx"], res["plus_di"], res["minus_di"], res["is_trending"])


calculate_ema = calc_ema
calculate_sma = calc_sma
calculate_macd = calc_macd


def analyze_price_structure(highs: Union[List[float], List[Any]], lows: Optional[List[float]] = None, lookback: int = 24) -> Dict[str, Any]:
    if highs and hasattr(highs[0], "high"):
        h_vals = [c.high for c in highs]
        l_vals = [c.low for c in highs]
    else:
        h_vals = highs
        l_vals = lows or []

    if len(h_vals) < lookback:
        return {"structure": "NEUTRAL", "trend_bias": "NEUTRAL", "hh_count": 0, "ll_count": 0}

    sub_h = h_vals[-lookback:]
    sub_l = l_vals[-lookback:]

    seg_size = lookback // 3
    h1, h2, h3 = max(sub_h[:seg_size]), max(sub_h[seg_size:seg_size*2]), max(sub_h[seg_size*2:])
    l1, l2, l3 = min(sub_l[:seg_size]), min(sub_l[seg_size:seg_size*2]), min(sub_l[seg_size*2:])

    is_bullish_structure = (h3 > h2 >= h1) and (l3 > l2 >= l1)
    is_bearish_structure = (h3 < h2 <= h1) and (l3 < l2 <= l1)

    if is_bullish_structure:
        return {"structure": "HIGHER_HIGHS_HIGHER_LOWS", "trend_bias": "BULLISH", "strength": 0.85}
    elif is_bearish_structure:
        return {"structure": "LOWER_HIGHS_LOWER_LOWS", "trend_bias": "BEARISH", "strength": 0.85}
    else:
        return {"structure": "MIXED_OR_RANGE", "trend_bias": "NEUTRAL", "strength": 0.3}
