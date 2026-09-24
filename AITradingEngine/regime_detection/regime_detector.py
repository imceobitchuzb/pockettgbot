"""
Market Regime Classification Engine.
Determines if current market is in Trend, Range, Breakout, Reversal, High/Low Volatility, Choppy, or Unstable.
Enforces the Zero-Forced-Signal principle by labeling choppy/unstable conditions as untradable.
"""
from typing import List, Dict, Any, Tuple
from AITradingEngine.core.enums import MarketRegime
from AITradingEngine.core.models import Candle
from AITradingEngine.regime_detection.noise_filter import evaluate_noise
from AITradingEngine.technical_analysis.trend import calculate_adx, calculate_ema
from AITradingEngine.technical_analysis.volatility import calculate_bollinger_bands, calculate_atr


class RegimeDetector:
    """Classifies the market regime for an asset timeframe."""

    def __init__(
        self,
        trend_adx_threshold: float = 25.0,
        chop_ci_threshold: float = 61.8,
        min_candles: int = 30
    ):
        self.trend_adx_threshold = trend_adx_threshold
        self.chop_ci_threshold = chop_ci_threshold
        self.min_candles = min_candles

    def detect(self, candles: List[Candle]) -> Tuple[MarketRegime, Dict[str, Any]]:
        """
        Detects market regime from closed candles.
        Returns (MarketRegime, details)
        """
        if len(candles) < self.min_candles:
            return MarketRegime.UNSTABLE, {"reason": "Insufficient candles for reliable regime detection"}

        noise = evaluate_noise(candles, period=14)
        adx_val, p_di, m_di = calculate_adx(candles, period=14)
        atr_val = calculate_atr(candles, period=14)
        bb = calculate_bollinger_bands(candles, period=20, std_dev=2.0)

        closes = [c.close for c in candles]
        ema9 = calculate_ema(closes, 9)
        ema21 = calculate_ema(closes, 21)
        ema50 = calculate_ema(closes, 50)

        last_close = closes[-1]
        e9 = ema9[-1]
        e21 = ema21[-1]
        e50 = ema50[-1]

        # 1. Check for extreme noise / chop first (Zero forced signal principle)
        if noise["choppiness_index"] >= self.chop_ci_threshold or noise["efficiency_ratio"] < 0.18:
            return MarketRegime.CHOPPY, {
                "adx": round(adx_val, 2),
                "choppiness": noise["choppiness_index"],
                "efficiency_ratio": noise["efficiency_ratio"],
                "reason": "Market in high noise / choppy phase"
            }

        # 2. Check for Volatility Squeeze / Low Volatility
        if bb.is_squeeze:
            return MarketRegime.LOW_VOLATILITY, {
                "bandwidth": round(bb.bandwidth, 5),
                "adx": round(adx_val, 2),
                "reason": "Bollinger squeeze - low volatility compression"
            }

        # 3. Check for Extreme Volatility / Breakout
        if bb.bandwidth > 0.008 or (atr_val > 0 and (candles[-1].high - candles[-1].low) > 2.8 * atr_val):
            # Check if breakout
            if last_close > bb.upper:
                return MarketRegime.BREAKOUT, {"direction": "UP", "bandwidth": round(bb.bandwidth, 5)}
            elif last_close < bb.lower:
                return MarketRegime.BREAKOUT, {"direction": "DOWN", "bandwidth": round(bb.bandwidth, 5)}
            return MarketRegime.HIGH_VOLATILITY, {"bandwidth": round(bb.bandwidth, 5)}

        # 4. Check for Strong Trending
        if adx_val >= self.trend_adx_threshold:
            if e9 > e21 > e50 and p_di > m_di and last_close > e21:
                return MarketRegime.TREND_UP, {
                    "adx": round(adx_val, 2),
                    "plus_di": round(p_di, 2),
                    "minus_di": round(m_di, 2),
                    "trend_strength": "STRONG_BULLISH"
                }
            elif e9 < e21 < e50 and m_di > p_di and last_close < e21:
                return MarketRegime.TREND_DOWN, {
                    "adx": round(adx_val, 2),
                    "plus_di": round(p_di, 2),
                    "minus_di": round(m_di, 2),
                    "trend_strength": "STRONG_BEARISH"
                }

        # 5. Check for Potential Reversal
        # Price at Bollinger extremities with divergence or cross back
        if last_close > bb.upper or last_close < bb.lower:
            return MarketRegime.REVERSAL, {
                "percent_b": round(bb.percent_b, 2),
                "reason": "Price tested outer Bollinger band with weakening ADX"
            }

        # 6. Default to RANGE if orderly oscillation
        return MarketRegime.RANGE, {
            "adx": round(adx_val, 2),
            "bandwidth": round(bb.bandwidth, 5),
            "reason": "Stable range oscillation"
        }
