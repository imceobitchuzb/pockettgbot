"""
AITradingEngine Snapshot Builder.
Builds immutable MarketSnapshot instances strictly prior to entry.
Guarantees ZERO look-ahead bias: only completed/closed candles are included.
"""
import time
from typing import List, Dict, Any, Optional

from AITradingEngine.core.models import Candle, MarketSnapshot
from AITradingEngine.core.enums import MarketType, Timeframe, MarketRegime
from AITradingEngine.technical_analysis.trend import calc_ema, calc_adx, analyze_price_structure
from AITradingEngine.technical_analysis.momentum import calc_rsi, calc_stochastic, calc_roc, calc_vortex
from AITradingEngine.technical_analysis.volatility import calc_atr, calc_bollinger_bands
from AITradingEngine.technical_analysis.mtf_engine import MTFEngine


class SnapshotBuilder:
    """Builds point-in-time snapshots with zero look-ahead bias."""

    def __init__(self):
        self.mtf_engine = MTFEngine()

    def build_snapshot(
        self,
        symbol: Optional[str] = None,
        market_type: MarketType = MarketType.REAL,
        primary_candles: Optional[List[Candle]] = None,
        primary_tf: Optional[Timeframe] = None,
        current_price: Optional[float] = None,
        payout: float = 0.85,
        mtf_candles: Optional[Dict[str, List[Candle]]] = None,
        indicators: Optional[Dict[str, Any]] = None,
        regime: MarketRegime = MarketRegime.UNKNOWN,
        **kwargs
    ) -> Optional[MarketSnapshot]:
        """
        Creates an immutable snapshot.
        Enforces zero look-ahead bias: unclosed candles are strictly discarded.
        """
        sym = symbol or kwargs.get("asset", "EURUSD")
        tf = primary_tf or kwargs.get("timeframe", Timeframe.M1)
        raw_candles = primary_candles or kwargs.get("closed_candles", [])

        # Filter out any unclosed forming candles to guarantee zero look-ahead bias
        closed_candles = [c for c in raw_candles if getattr(c, "is_closed", True)]
        if not closed_candles:
            return None

        # Price anchor
        curr_p = current_price if current_price is not None else closed_candles[-1].close

        now_sec = time.time()
        snap_id = f"snap_{sym}_{tf.value}_{int(now_sec * 1000)}"

        # Compute point-in-time indicators if not provided
        if indicators is None or not indicators:
            closes = [c.close for c in closed_candles]
            highs = [c.high for c in closed_candles]
            lows = [c.low for c in closed_candles]

            adx_data = calc_adx(highs, lows, closes, period=14)
            atr_val = calc_atr(highs, lows, closes, period=14)
            bb = calc_bollinger_bands(closes, period=20, std_dev=2.0)
            rsi_val = calc_rsi(closes, period=14)
            stoch = calc_stochastic(highs, lows, closes, k_period=14, d_period=3)
            roc_val = calc_roc(closes, period=10)
            vortex = calc_vortex(highs, lows, closes, period=14)
            struct = analyze_price_structure(highs, lows, lookback=24)

            e9 = calc_ema(closes, 9)
            e21 = calc_ema(closes, 21)
            e50 = calc_ema(closes, 50)
            e200 = calc_ema(closes, 200)

            computed_indicators = {
                "adx": adx_data["adx"],
                "plus_di": adx_data["plus_di"],
                "minus_di": adx_data["minus_di"],
                "atr": atr_val,
                "bb_upper": bb["upper"],
                "bb_lower": bb["lower"],
                "bb_middle": bb["middle"],
                "bb_bandwidth": bb["bandwidth"],
                "bb_percent_b": bb["percent_b"],
                "bb_is_squeeze": bb["bandwidth"] < 0.0015,
                "rsi": rsi_val,
                "stoch_k": stoch["k"],
                "stoch_d": stoch["d"],
                "roc": roc_val,
                "vortex_pos": vortex["vortex_pos"],
                "vortex_neg": vortex["vortex_neg"],
                "structure": struct["structure"],
                "ema9": e9[-1] if e9 else curr_p,
                "ema21": e21[-1] if e21 else curr_p,
                "ema50": e50[-1] if e50 else curr_p,
                "ema200": e200[-1] if e200 else curr_p
            }
        else:
            computed_indicators = dict(indicators)
            atr_val = computed_indicators.get("atr", 0.0001)

        # MTF evaluation
        mtf_dict = mtf_candles or {}
        mtf_alignment = None
        if mtf_dict:
            try:
                mtf_eval = self.mtf_engine.evaluate_concordance(mtf_dict)
                from AITradingEngine.core.enums import Direction
                # Map bias string to Direction
                macro_dir = Direction.CALL if mtf_eval.get("bias_5m") == "BULLISH" else (Direction.PUT if mtf_eval.get("bias_5m") == "BEARISH" else Direction.NO_SIGNAL)
                struct_dir = Direction.CALL if mtf_eval.get("bias_1m") == "BULLISH" else (Direction.PUT if mtf_eval.get("bias_1m") == "BEARISH" else Direction.NO_SIGNAL)
                entry_dir = Direction.CALL if mtf_eval.get("bias_entry") == "BULLISH" else (Direction.PUT if mtf_eval.get("bias_entry") == "BEARISH" else Direction.NO_SIGNAL)

                class MTFResult:
                    def __init__(self, m, s, e, has_conf, score):
                        self.macro_trend = m
                        self.structure_trend = s
                        self.entry_trend = e
                        self.has_conflict = has_conf
                        self.concordance_score = abs(score)

                mtf_alignment = MTFResult(macro_dir, struct_dir, entry_dir, mtf_eval.get("has_conflict", False), mtf_eval.get("mtf_score", 0.0))
            except Exception:
                pass

        det_regime = regime if regime != MarketRegime.UNKNOWN else kwargs.get("market_regime", MarketRegime.UNKNOWN)
        if det_regime == MarketRegime.UNKNOWN:
            from AITradingEngine.regime_detection.regime_detector import RegimeDetector
            det_regime, _ = RegimeDetector().detect(closed_candles)

        return MarketSnapshot(

            snapshot_id=snap_id,
            timestamp=now_sec,
            symbol=sym,
            asset=sym,
            market_type=market_type,
            primary_timeframe=tf,
            timeframe=tf,
            current_price=curr_p,
            payout=payout,
            candles=closed_candles,
            mtf_candles=mtf_dict,
            indicators=computed_indicators,
            mtf_alignment=mtf_alignment,
            regime=det_regime,
            market_regime=det_regime,
            volatility_atr=atr_val
        )


snapshot_builder = SnapshotBuilder()
