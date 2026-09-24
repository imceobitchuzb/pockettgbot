"""
Strategy 7: Mean Reversion.
Operates in range environments when price extends to statistical extremes of Bollinger Bands and RSI.
"""
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, StrategyVote
from AITradingEngine.strategy_engine.base_strategy import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """Mean Reversion Strategy."""

    def __init__(self, weight: float = 1.1):
        super().__init__(name="MeanReversion", weight=weight)

    def evaluate(self, snapshot: MarketSnapshot) -> StrategyVote:
        if not self.is_active:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Strategy inactive", self.weight)

        # STRICT: Only allow mean reversion in RANGE or REVERSAL regimes, NEVER in strong TREND_UP or TREND_DOWN!
        if snapshot.regime in (MarketRegime.TREND_UP, MarketRegime.TREND_DOWN, MarketRegime.CHOPPY, MarketRegime.UNSTABLE):
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, f"Unsuitable regime for mean reversion ({snapshot.regime.value})", self.weight)

        ind = snapshot.indicators
        rsi = ind.get("rsi", 50.0)
        pct_b = ind.get("bb_percent_b", 0.5)
        stoch_k = ind.get("stoch_k", 50.0)
        stoch_d = ind.get("stoch_d", 50.0)

        # Oversold Reversion (CALL):
        # Price below lower Bollinger Band (%B < 0.05), RSI < 30, Stoch hook up (%K > %D)
        if pct_b <= 0.05 and rsi <= 30.0 and stoch_k > stoch_d:
            conf = 0.78
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.CALL,
                confidence=conf,
                reasoning=f"Statistical oversold extension (%B={pct_b:.2f}, RSI={rsi:.1f}, StochK={stoch_k:.1f}) in range",
                weight=self.weight
            )

        # Overbought Reversion (PUT):
        # Price above upper Bollinger Band (%B > 0.95), RSI > 70, Stoch hook down (%K < %D)
        if pct_b >= 0.95 and rsi >= 70.0 and stoch_k < stoch_d:
            conf = 0.78
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.PUT,
                confidence=conf,
                reasoning=f"Statistical overbought extension (%B={pct_b:.2f}, RSI={rsi:.1f}, StochK={stoch_k:.1f}) in range",
                weight=self.weight
            )

        return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "No statistical mean reversion extreme", self.weight)
