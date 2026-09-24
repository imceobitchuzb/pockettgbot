"""
Market Quality Ranker.
Computes a comprehensive Market Quality Score (0-100) based on volatility, trend clarity,
noise filtering, and broker payout. Untradable markets are assigned is_tradable=False.
"""
from typing import List
from AITradingEngine.core.enums import MarketRegime
from AITradingEngine.core.models import Candle, MarketQualityScore
from AITradingEngine.regime_detection.noise_filter import evaluate_noise
from AITradingEngine.technical_analysis.trend import calculate_adx
from AITradingEngine.technical_analysis.volatility import calculate_atr


def compute_market_quality(
    candles: List[Candle],
    regime: MarketRegime,
    payout: float = 0.85,
    min_quality_score: float = 65.0
) -> MarketQualityScore:
    """
    Evaluates market quality for trading.
    Weights:
    - Regime / Trend clarity: 35 points
    - Noise & Choppiness: 25 points
    - Volatility appropriateness: 20 points
    - Broker Payout: 20 points
    """
    if len(candles) < 20:
        return MarketQualityScore(
            trend_clarity=0.0,
            volatility_health=0.0,
            noise_penalty=50.0,
            payout_score=0.0,
            total_score=0.0,
            is_tradable=False,
            notes="Insufficient candle history"
        )

    # 1. Regime / Trend clarity (max 35)
    trend_score = 0.0
    adx_val, _, _ = calculate_adx(candles, period=14)
    if regime in (MarketRegime.TREND_UP, MarketRegime.TREND_DOWN):
        trend_score = min(35.0, 15.0 + (adx_val / 50.0) * 20.0)
    elif regime == MarketRegime.RANGE:
        trend_score = 22.0  # Stable range can be traded on mean reversion
    elif regime == MarketRegime.BREAKOUT:
        trend_score = 26.0
    elif regime in (MarketRegime.CHOPPY, MarketRegime.UNSTABLE):
        trend_score = 0.0
    else:
        trend_score = 10.0

    # 2. Noise evaluation (max 25)
    noise = evaluate_noise(candles, period=14)
    ci = noise["choppiness_index"]
    er = noise["efficiency_ratio"]
    # Best CI < 38.2, worst CI > 61.8
    ci_score = max(0.0, min(15.0, (61.8 - ci) / (61.8 - 38.2) * 15.0))
    er_score = min(10.0, er * 12.0)
    noise_score = ci_score + er_score
    noise_penalty = 25.0 - noise_score

    # 3. Volatility Health (max 20)
    atr = calculate_atr(candles, period=14)
    avg_price = sum(c.close for c in candles[-14:]) / 14.0
    atr_pct = (atr / avg_price) * 100.0 if avg_price > 0 else 0.0

    # Ideal ATR percent is between 0.02% and 0.25%
    if 0.02 <= atr_pct <= 0.25:
        volatility_score = 20.0
    elif atr_pct < 0.01:  # Dead market
        volatility_score = 4.0
    elif atr_pct > 0.45:  # Extreme erratic volatility
        volatility_score = 6.0
    else:
        volatility_score = 14.0

    # 4. Broker Payout Score (max 20)
    # Binary options requires high payout (>=80%) to maintain statistical edge
    if payout >= 0.85:
        payout_score = 20.0
    elif payout >= 0.80:
        payout_score = 15.0
    elif payout >= 0.70:
        payout_score = 6.0
    else:
        payout_score = 0.0

    total_score = round(trend_score + noise_score + volatility_score + payout_score, 1)

    # Hard disqualify if choppy, unstable, or payout too low (< 75%)
    is_tradable = (
        total_score >= min_quality_score and
        regime not in (MarketRegime.CHOPPY, MarketRegime.UNSTABLE) and
        payout >= 0.75 and
        not noise["is_noisy"]
    )

    notes = []
    if noise["is_noisy"]:
        notes.append("High Noise / Choppiness")
    if regime in (MarketRegime.CHOPPY, MarketRegime.UNSTABLE):
        notes.append(f"Regime {regime.value} untradable")
    if payout < 0.80:
        notes.append(f"Suboptimal payout ({int(payout*100)}%)")
    if is_tradable:
        notes.append("Market conditions favorable")

    return MarketQualityScore(
        trend_clarity=round(trend_score, 1),
        volatility_health=round(volatility_score, 1),
        noise_penalty=round(noise_penalty, 1),
        payout_score=round(payout_score, 1),
        total_score=total_score,
        is_tradable=is_tradable,
        notes="; ".join(notes)
    )
