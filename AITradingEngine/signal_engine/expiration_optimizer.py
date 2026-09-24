"""
Expiration Optimizer.
Selects optimal expiration duration (15s, 30s, 1m, 2m, 3m, 5m) based on
setup archetype, timeframe, and volatility regime.
"""
from typing import Dict, Any
from AITradingEngine.core.enums import Timeframe, MarketRegime


class ExpirationOptimizer:
    """Optimizes option expiration time based on quantitative backtest models."""

    def __init__(self):
        # Default mapping of strategy archetypes to candle horizons
        self.archetype_horizons = {
            "SRRejection": 1,        # Fast reaction bounce (1 candle)
            "FalseBreakout": 2,      # Mean reversion back into range (1-2 candles)
            "TrendFollowing": 3,     # Trend continuation runway (2-3 candles)
            "TrendPullback": 2,      # Resumption off EMA (2 candles)
            "BreakoutConfirm": 2,    # Momentum continuation (2 candles)
            "MomentumPulse": 1,      # Quick momentum surge (1-2 candles)
            "MeanReversion": 2,      # Return to middle Bollinger Band (2 candles)
            "VolatilityRegime": 3,   # Multi-candle expansion
            "MTFConfluence": 2       # Concordance flow
        }

    def optimize_expiration(
        self,
        timeframe: Timeframe,
        setup_name: str,
        regime: MarketRegime,
        atr: float
    ) -> Dict[str, Any]:
        """
        Determines the optimal expiration string and duration in seconds.
        """
        horizon_candles = self.archetype_horizons.get(setup_name, 2)

        # Base seconds per timeframe
        tf_seconds_map = {
            Timeframe.TF_5S: 5,
            Timeframe.TF_15S: 15,
            Timeframe.TF_30S: 30,
            Timeframe.TF_1M: 60,
            Timeframe.TF_5M: 300,
            Timeframe.TF_15M: 900
        }

        candle_sec = tf_seconds_map.get(timeframe, 60)
        target_sec = candle_sec * horizon_candles

        # Normalize to standard Pocket Option expiration intervals
        # Standard: 15s, 30s, 1m (60s), 2m (120s), 3m (180s), 5m (300s)
        if target_sec <= 20:
            selected_sec = 15
            label = "15 SEC"
        elif target_sec <= 45:
            selected_sec = 30
            label = "30 SEC"
        elif target_sec <= 90:
            selected_sec = 60
            label = "1 MIN"
        elif target_sec <= 150:
            selected_sec = 120
            label = "2 MIN"
        elif target_sec <= 210:
            selected_sec = 180
            label = "3 MIN"
        else:
            selected_sec = 300
            label = "5 MIN"

        # If regime is high volatility, shorten duration to mitigate late reversal risk
        if regime == MarketRegime.HIGH_VOLATILITY and selected_sec > 60:
            selected_sec = 60
            label = "1 MIN"

        return {
            "expiration_sec": selected_sec,
            "expiration_label": label,
            "candles_horizon": horizon_candles,
            "notes": f"Optimized for {setup_name} on {timeframe.value} ({label})"
        }
