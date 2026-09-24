"""
AITradingEngine Multi-Timeframe Engine (MTF)
Analyzes Higher Timeframe (5m Macro), Middle Timeframe (1m Structure), and Entry Timeframe (15s/30s Setup).
Calculates MTF Concordance Score and aggressively flags contradictory timeframe structures.
"""
from typing import Dict, List, Any, Optional
from AITradingEngine.core.models import Candle
from AITradingEngine.technical_analysis.trend import calc_ema

class MTFEngine:
    def evaluate_concordance(self, mtf_candles: Dict[str, List[Candle]]) -> Dict[str, Any]:
        """
        Evaluates 5m (macro), 1m (structure), 15s/30s (entry).
        """
        c_5m = mtf_candles.get("5m", [])
        c_1m = mtf_candles.get("1m", [])
        c_entry = mtf_candles.get("15s", mtf_candles.get("30s", []))

        bias_5m = self._get_timeframe_bias(c_5m)
        bias_1m = self._get_timeframe_bias(c_1m)
        bias_entry = self._get_timeframe_bias(c_entry)

        # Numerical mapping: Bullish = +1, Bearish = -1, Neutral = 0
        score_5m = 1.0 if bias_5m == "BULLISH" else (-1.0 if bias_5m == "BEARISH" else 0.0)
        score_1m = 1.0 if bias_1m == "BULLISH" else (-1.0 if bias_1m == "BEARISH" else 0.0)
        score_entry = 1.0 if bias_entry == "BULLISH" else (-1.0 if bias_entry == "BEARISH" else 0.0)

        # Weighted MTF Score: 5m (0.45), 1m (0.35), entry (0.20)
        total_score = round(score_5m * 0.45 + score_1m * 0.35 + score_entry * 0.20, 2)

        # Conflict check: Higher timeframe directly opposes entry
        conflict = False
        conflict_reason = None

        if (score_5m > 0 and score_entry < -0.5) or (score_5m < 0 and score_entry > 0.5):
            conflict = True
            conflict_reason = f"MTF_DISAGREEMENT: 5m Macro is {bias_5m} but Entry is {bias_entry}"

        return {
            "bias_5m": bias_5m,
            "bias_1m": bias_1m,
            "bias_entry": bias_entry,
            "mtf_score": total_score,
            "has_conflict": conflict,
            "conflict_reason": conflict_reason,
            "is_aligned_bullish": total_score >= 0.70 and not conflict,
            "is_aligned_bearish": total_score <= -0.70 and not conflict
        }

    def _get_timeframe_bias(self, candles: List[Candle]) -> str:
        if len(candles) < 10:
            return "NEUTRAL"
        closes = [c.close for c in candles]
        ema_fast = calc_ema(closes, 9)
        ema_slow = calc_ema(closes, 21)

        cur_c = closes[-1]
        cur_fast = ema_fast[-1]
        cur_slow = ema_slow[-1]

        if cur_c > cur_fast > cur_slow:
            return "BULLISH"
        elif cur_c < cur_fast < cur_slow:
            return "BEARISH"
        else:
            return "NEUTRAL"

mtf_engine = MTFEngine()
MTFConcordanceEngine = MTFEngine
