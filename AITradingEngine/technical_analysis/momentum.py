"""
AITradingEngine Momentum Module.
Implements RSI (Wilder), Stochastic (%K, %D), Rate of Change (ROC), Vortex, and Aroon.
"""
import math
from typing import List, Dict, Any, Tuple, Union


class VortexResult(tuple):
    def __new__(cls, vi_plus: float, vi_minus: float):
        obj = tuple.__new__(cls, (vi_plus, vi_minus))
        obj.vortex_pos = vi_plus
        obj.vortex_neg = vi_minus
        obj.vi_plus = vi_plus
        obj.vi_minus = vi_minus
        return obj

    def __getitem__(self, item):
        if isinstance(item, str):
            if item in ("vortex_pos", "vi_plus"):
                return self.vortex_pos
            elif item in ("vortex_neg", "vi_minus"):
                return self.vortex_neg
            raise KeyError(item)
        return tuple.__getitem__(self, item)


class AroonResult(tuple):
    def __new__(cls, aroon_up: float, aroon_down: float):
        obj = tuple.__new__(cls, (aroon_up, aroon_down))
        obj.aroon_up = aroon_up
        obj.aroon_down = aroon_down
        return obj

    def __getitem__(self, item):
        if isinstance(item, str):
            if item == "aroon_up":
                return self.aroon_up
            elif item == "aroon_down":
                return self.aroon_down
            raise KeyError(item)
        return tuple.__getitem__(self, item)


def calc_rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) <= period:
        return 50.0

    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(diff if diff > 0 else 0.0)
        losses.append(abs(diff) if diff < 0 else 0.0)

    # Wilder's smoothing
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)


def calc_stochastic(highs: List[float], lows: List[float], closes: List[float],
                    k_period: int = 14, d_period: int = 3) -> Dict[str, Any]:
    n = len(closes)
    if n < k_period + d_period:
        return {"k": 50.0, "d": 50.0, "is_overbought": False, "is_oversold": False}

    k_values = []
    for i in range(k_period, n + 1):
        window_high = max(highs[i - k_period : i])
        window_low = min(lows[i - k_period : i])
        current_close = closes[i - 1]
        rng = window_high - window_low
        k_val = ((current_close - window_low) / rng * 100.0) if rng > 0 else 50.0
        k_values.append(k_val)

    current_k = round(k_values[-1], 2)
    d_slice = k_values[-d_period:]
    current_d = round(sum(d_slice) / len(d_slice), 2) if d_slice else current_k

    return {
        "k": current_k,
        "d": current_d,
        "is_overbought": current_k >= 80.0,
        "is_oversold": current_k <= 20.0
    }


def calc_roc(closes: List[float], period: int = 12) -> float:
    if len(closes) <= period or closes[-period - 1] == 0:
        return 0.0
    return round(((closes[-1] - closes[-period - 1]) / closes[-period - 1]) * 100.0, 3)


def calc_momentum(closes: List[float], period: int = 10) -> float:
    if len(closes) <= period:
        return 0.0
    return round(closes[-1] - closes[-period - 1], 5)


def calc_vortex(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> VortexResult:
    n = len(closes)
    if n <= period + 1:
        return VortexResult(1.0, 1.0)
    tr = [0.0] * n
    vm_plus = [0.0] * n
    vm_minus = [0.0] * n

    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        vm_plus[i] = abs(highs[i] - lows[i - 1])
        vm_minus[i] = abs(lows[i] - highs[i - 1])

    sum_tr = sum(tr[-period:])
    sum_vm_plus = sum(vm_plus[-period:])
    sum_vm_minus = sum(vm_minus[-period:])

    vi_plus = round(sum_vm_plus / sum_tr, 3) if sum_tr > 0 else 1.0
    vi_minus = round(sum_vm_minus / sum_tr, 3) if sum_tr > 0 else 1.0
    return VortexResult(vi_plus, vi_minus)


def calc_aroon(highs: List[float], lows: List[float], period: int = 15) -> AroonResult:
    n = len(highs)
    if n <= period:
        return AroonResult(50.0, 50.0)
    window_highs = highs[-period - 1:]
    window_lows = lows[-period - 1:]

    max_idx = max(range(len(window_highs)), key=lambda k: window_highs[k])
    min_idx = min(range(len(window_lows)), key=lambda k: window_lows[k])

    periods_since_high = period - max_idx
    periods_since_low = period - min_idx

    aroon_up = round(((period - periods_since_high) / period) * 100.0, 1)
    aroon_down = round(((period - periods_since_low) / period) * 100.0, 1)
    return AroonResult(aroon_up, aroon_down)
