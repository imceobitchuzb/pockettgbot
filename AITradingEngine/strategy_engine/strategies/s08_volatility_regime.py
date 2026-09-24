"""
Strategy 8: Volatility Regime (Squeeze Expansion).
Detects explosive volatility expansion following a period of tight Bollinger band compression.
"""
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, StrategyVote
from AITradingEngine.strategy_engine.base_strategy import BaseStrategy


class VolatilityRegimeStrategy(BaseStrategy):
    """Volatility Regime Strategy."""

    def __init__(self, weight: float = 1.05):
        super().__init__(name="VolatilityRegime", weight=weight)

    def evaluate(self, snapshot: MarketSnapshot) -> StrategyVote:
        if not self.is_active:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Strategy inactive", self.weight)

        if snapshot.regime in (MarketRegime.CHOPPY, MarketRegime.UNSTABLE):
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Regime untradable", self.weight)

        ind = snapshot.indicators
        bw = ind.get("bb_bandwidth", 0.0)
        is_sq = ind.get("bb_is_squeeze", False)
        upper = ind.get("bb_upper", 0.0)
        lower = ind.get("bb_lower", 0.0)
        mid = ind.get("bb_middle", 0.0)

        if len(snapshot.candles) < 3:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Insufficient candles", self.weight)

        curr = snapshot.candles[-1]

        # Breakout expansion upwards out of compression
        if curr.close > upper and curr.close > curr.open:
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.CALL,
                confidence=0.75,
                reasoning=f"Volatility expansion break above upper band (Bandwidth={bw:.4f})",
                weight=self.weight
            )

        # Breakout expansion downwards out of compression
        if curr.close < lower and curr.close < curr.open:
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.PUT,
                confidence=0.75,
                reasoning=f"Volatility expansion break below lower band (Bandwidth={bw:.4f})",
                weight=self.weight
            )

        return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "No volatility expansion event", self.weight)
