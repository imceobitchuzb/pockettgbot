"""
AITradingEngine Multi-Timeframe Engine (MTF).
Analyzes strictly closed bars across 1M (Execution), 3M (Intermediate), 5M (Trend), and 15M (Macro).
Calculates weighted concordance and strictly flags conflicting timeframes.
"""
from typing import Dict, List, Any, Optional
from AITradingEngine.core.models import Candle
from AITradingEngine.technical_analysis.trend import calc_ema


class MTFEngine:
    """
    Weighted Multi-Timeframe Engine across 1M, 3M, 5M, 15M.
    Enforces that trade direction on 1M is confirmed by higher timeframe structure.
    """

    def evaluate_concordance(self, mtf_candles: Dict[str, List[Candle]]) -> Dict[str, Any]:
        c_1m = mtf_candles.get("1m", mtf_candles.get("1M", []))
        c_3m = mtf_candles.get("3m", mtf_candles.get("3M", []))
        c_5m = mtf_candles.get("5m", mtf_candles.get("5M", []))
        c_15m = mtf_candles.get("15m", mtf_candles.get("15M", []))

        bias_1m = self._get_timeframe_bias(c_1m)
        bias_3m = self._get_timeframe_bias(c_3m)
        bias_5m = self._get_timeframe_bias(c_5m)
        bias_15m = self._get_timeframe_bias(c_15m)

        def score_bias(bias: str) -> float:
            return 1.0 if bias == "BULLISH" else (-1.0 if bias == "BEARISH" else 0.0)

        s_1m = score_bias(bias_1m)
        s_3m = score_bias(bias_3m)
        s_5m = score_bias(bias_5m)
        s_15m = score_bias(bias_15m)

        # Weighted MTF Score: 1M (0.40), 3M (0.25), 5M (0.20), 15M (0.15)
        # If higher timeframes are empty/insufficient, fallback gracefully without bias
        active_weights = 0.40
        weighted_sum = s_1m * 0.40

        if len(c_3m) >= 5:
            weighted_sum += s_3m * 0.25
            active_weights += 0.25
        if len(c_5m) >= 5:
            weighted_sum += s_5m * 0.20
            active_weights += 0.20
        if len(c_15m) >= 5:
            weighted_sum += s_15m * 0.15
            active_weights += 0.15

        norm_score = round(weighted_sum / active_weights, 2) if active_weights > 0 else 0.0

        # Strict conflict detection:
        # If 1M is Bullish (+1) but 5M or 15M is Bearish (-1) => Hard Conflict
        # If 1M is Bearish (-1) but 5M or 15M is Bullish (+1) => Hard Conflict
        conflict = False
        conflict_reason = None

        if s_1m > 0 and (s_5m < 0 or s_15m < 0):
            conflict = True
            conflict_reason = f"MTF_DISAGREEMENT: 1M is BULLISH but higher timeframe (5M:{bias_5m}, 15M:{bias_15m}) is BEARISH"
        elif s_1m < 0 and (s_5m > 0 or s_15m > 0):
            conflict = True
            conflict_reason = f"MTF_DISAGREEMENT: 1M is BEARISH but higher timeframe (5M:{bias_5m}, 15M:{bias_15m}) is BULLISH"
        elif s_1m > 0 and s_3m < 0:
            conflict = True
            conflict_reason = f"MTF_DISAGREEMENT: 1M is BULLISH but 3M is BEARISH"
        elif s_1m < 0 and s_3m > 0:
            conflict = True
            conflict_reason = f"MTF_DISAGREEMENT: 1M is BEARISH but 3M is BULLISH"

        return {
            "bias_1m": bias_1m,
            "bias_3m": bias_3m,
            "bias_5m": bias_5m,
            "bias_15m": bias_15m,
            "mtf_score": norm_score,
            "has_conflict": conflict,
            "conflict_reason": conflict_reason,
            "is_aligned_bullish": (norm_score >= 0.60) and not conflict,
            "is_aligned_bearish": (norm_score <= -0.60) and not conflict,
            # Legacy compatibility fields
            "bias_entry": bias_1m
        }

    def _get_timeframe_bias(self, candles: List[Candle]) -> str:
        if not candles or len(candles) < 5:
            return "NEUTRAL"
        closes = [c.close for c in candles]
        p_fast = min(9, len(closes))
        p_slow = min(21, len(closes))
        ema_fast = calc_ema(closes, p_fast)
        ema_slow = calc_ema(closes, p_slow)

        cur_c = closes[-1]
        cur_fast = ema_fast[-1]
        cur_slow = ema_slow[-1]

        if cur_c > cur_fast and cur_fast >= cur_slow:
            return "BULLISH"
        elif cur_c < cur_fast and cur_fast <= cur_slow:
            return "BEARISH"
        else:
            return "NEUTRAL"


mtf_engine = MTFEngine()
MTFConcordanceEngine = MTFEngine
