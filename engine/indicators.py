import math
from typing import List, Dict, Any, Tuple, Optional

def calc_ema(values: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average (EMA)."""
    if len(values) < period:
        return values.copy()
    ema = [0.0] * len(values)
    multiplier = 2.0 / (period + 1.0)
    
    # Initialize with SMA
    sma = sum(values[:period]) / period
    ema[period - 1] = sma
    for i in range(period):
        ema[i] = values[i]
        
    for i in range(period, len(values)):
        ema[i] = (values[i] - ema[i - 1]) * multiplier + ema[i - 1]
    return ema


def calc_rsi(closes: List[float], period: int = 14) -> List[float]:
    """Calculate Relative Strength Index (RSI)."""
    if len(closes) <= period:
        return [50.0] * len(closes)
    
    rsi = [50.0] * len(closes)
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    
    gains = [max(0.0, d) for d in deltas]
    losses = [max(0.0, -d) for d in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))
        
    for i in range(period + 1, len(closes)):
        delta_idx = i - 1
        gain = gains[delta_idx]
        loss = losses[delta_idx]
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
            
    return rsi


def calc_parabolic_sar(highs: List[float], lows: List[float], closes: List[float],
                       af_step: float = 0.02, af_max: float = 0.2) -> Tuple[List[float], List[bool]]:
    """
    Calculate Parabolic SAR (Stop and Reverse).
    Returns (sar_values, is_uptrend_flags).
    """
    n = len(closes)
    if n < 3:
        return closes.copy(), [True] * n
        
    sar = [0.0] * n
    is_uptrend = [True] * n
    
    # Initialize
    uptrend = closes[1] >= closes[0]
    is_uptrend[0] = uptrend
    is_uptrend[1] = uptrend
    
    if uptrend:
        sar[1] = min(lows[0], lows[1])
        ep = max(highs[0], highs[1])
    else:
        sar[1] = max(highs[0], highs[1])
        ep = min(lows[0], lows[1])
        
    sar[0] = sar[1]
    af = af_step
    
    for i in range(2, n):
        prev_sar = sar[i - 1]
        
        if uptrend:
            cur_sar = prev_sar + af * (ep - prev_sar)
            # SAR cannot be higher than low of previous 2 periods
            cur_sar = min(cur_sar, lows[i - 1], lows[i - 2])
            
            if lows[i] < cur_sar:
                # Reversal to downtrend
                uptrend = False
                cur_sar = ep
                ep = lows[i]
                af = af_step
            else:
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_step, af_max)
        else:
            cur_sar = prev_sar + af * (ep - prev_sar)
            # SAR cannot be lower than high of previous 2 periods
            cur_sar = max(cur_sar, highs[i - 1], highs[i - 2])
            
            if highs[i] > cur_sar:
                # Reversal to uptrend
                uptrend = True
                cur_sar = ep
                ep = highs[i]
                af = af_step
            else:
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_step, af_max)
                    
        sar[i] = cur_sar
        is_uptrend[i] = uptrend
        
    return sar, is_uptrend


def calc_vortex(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Tuple[List[float], List[float]]:
    """
    Calculate Vortex Indicator (VI+ and VI-).
    """
    n = len(closes)
    vi_plus = [1.0] * n
    vi_minus = [1.0] * n
    
    if n <= period + 1:
        return vi_plus, vi_minus
        
    tr = [0.0] * n
    vm_plus = [0.0] * n
    vm_minus = [0.0] * n
    
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        vm_plus[i] = abs(highs[i] - lows[i - 1])
        vm_minus[i] = abs(lows[i] - highs[i - 1])
        
    for i in range(period, n):
        sum_tr = sum(tr[i - period + 1: i + 1])
        sum_vm_plus = sum(vm_plus[i - period + 1: i + 1])
        sum_vm_minus = sum(vm_minus[i - period + 1: i + 1])
        
        if sum_tr > 0:
            vi_plus[i] = round(sum_vm_plus / sum_tr, 4)
            vi_minus[i] = round(sum_vm_minus / sum_tr, 4)
            
    return vi_plus, vi_minus


def calc_aroon(highs: List[float], lows: List[float], period: int = 15) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate Aroon Indicator (Aroon Up, Aroon Down, Aroon Oscillator).
    """
    n = len(highs)
    aroon_up = [50.0] * n
    aroon_down = [50.0] * n
    aroon_osc = [0.0] * n
    
    if n <= period:
        return aroon_up, aroon_down, aroon_osc
        
    for i in range(period, n):
        window_highs = highs[i - period: i + 1]
        window_lows = lows[i - period: i + 1]
        
        # Periods since highest high and lowest low
        max_idx = max(range(len(window_highs)), key=lambda k: window_highs[k])
        min_idx = min(range(len(window_lows)), key=lambda k: window_lows[k])
        
        periods_since_high = period - max_idx
        periods_since_low = period - min_idx
        
        up = ((period - periods_since_high) / period) * 100.0
        down = ((period - periods_since_low) / period) * 100.0
        
        aroon_up[i] = round(up, 2)
        aroon_down[i] = round(down, 2)
        aroon_osc[i] = round(up - down, 2)
        
    return aroon_up, aroon_down, aroon_osc


def calc_zigzag(highs: List[float], lows: List[float], closes: List[float],
                depth: int = 12, deviation: float = 0.05, backstep: int = 3) -> Dict[str, Any]:
    """
    Calculate ZigZag swing points and current trend.
    deviation is percent threshold (e.g. 0.05 = 0.05%).
    """
    n = len(closes)
    if n < depth:
        return {"points": [], "current_trend": "neutral", "last_pivot": "none"}
        
    points = [] # list of {"index": i, "price": p, "type": "high"|"low"}
    
    # Identify swing highs and lows
    for i in range(depth, n - backstep):
        cur_high = highs[i]
        cur_low = lows[i]
        
        is_highest = all(cur_high >= highs[k] for k in range(i - depth, i + 1))
        is_lowest = all(cur_low <= lows[k] for k in range(i - depth, i + 1))
        
        if is_highest:
            if not points or points[-1]["type"] != "high":
                points.append({"index": i, "price": cur_high, "type": "high"})
            elif cur_high > points[-1]["price"]:
                points[-1] = {"index": i, "price": cur_high, "type": "high"}
        elif is_lowest:
            if not points or points[-1]["type"] != "low":
                points.append({"index": i, "price": cur_low, "type": "low"})
            elif cur_low < points[-1]["price"]:
                points[-1] = {"index": i, "price": cur_low, "type": "low"}
                
    trend = "neutral"
    last_pivot = "none"
    if points:
        last_pivot = points[-1]["type"]
        if last_pivot == "low":
            trend = "up" # Bounced from low, heading up
        else:
            trend = "down" # Rejection from high, heading down
            
    return {
        "points": points,
        "current_trend": trend,
        "last_pivot": last_pivot
    }


def calc_bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    """Calculate Bollinger Bands (Middle, Upper, Lower)."""
    n = len(closes)
    middle = closes.copy()
    upper = closes.copy()
    lower = closes.copy()
    
    if n < period:
        return middle, upper, lower
        
    for i in range(period - 1, n):
        slice_vals = closes[i - period + 1: i + 1]
        m = sum(slice_vals) / period
        variance = sum((x - m) ** 2 for x in slice_vals) / period
        std = math.sqrt(variance)
        
        middle[i] = round(m, 5)
        upper[i] = round(m + std_dev * std, 5)
        lower[i] = round(m - std_dev * std, 5)
        
    return middle, upper, lower


def calc_macd(closes: List[float], fast: int = 12, slow: int = 26, signal_period: int = 9) -> Dict[str, List[float]]:
    """Calculate MACD (MACD line, Signal line, Histogram)."""
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


def calc_fractals(highs: List[float], lows: List[float], period: int = 4) -> Dict[str, List[Dict[str, Any]]]:
    """Calculate Bill Williams Fractals."""
    n = len(highs)
    up_fractals = []
    down_fractals = []
    
    if n < 5:
        return {"up": up_fractals, "down": down_fractals}
        
    for i in range(2, n - 2):
        # Bearish fractal (Peak / Up Fractal)
        if highs[i] > highs[i - 1] and highs[i] > highs[i - 2] and highs[i] > highs[i + 1] and highs[i] > highs[i + 2]:
            up_fractals.append({"index": i, "price": highs[i]})
            
        # Bullish fractal (Trough / Down Fractal)
        if lows[i] < lows[i - 1] and lows[i] < lows[i - 2] and lows[i] < lows[i + 1] and lows[i] < lows[i + 2]:
            down_fractals.append({"index": i, "price": lows[i]})
            
    return {"up": up_fractals, "down": down_fractals}
