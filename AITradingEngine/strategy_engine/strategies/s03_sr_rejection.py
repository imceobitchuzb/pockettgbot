"""
Strategy 3: Support / Resistance Rejection.
Enters on confirmed rejection of established horizontal price levels with pinbar or reversal candlestick.
"""
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, StrategyVote
from AITradingEngine.strategy_engine.base_strategy import BaseStrategy
from AITradingEngine.pattern_engine.price_action import detect_sr_levels, check_sr_rejection


class SRRejectionStrategy(BaseStrategy):
    """Support and Resistance Rejection Strategy."""

    def __init__(self, weight: float = 1.1):
        super().__init__(name="SRRejection", weight=weight)

    def evaluate(self, snapshot: MarketSnapshot) -> StrategyVote:
        if not self.is_active:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Strategy inactive", self.weight)

        if snapshot.regime in (MarketRegime.CHOPPY, MarketRegime.UNSTABLE):
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Market regime untradable", self.weight)

        if len(snapshot.candles) < 25:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Insufficient candle history", self.weight)

        atr = snapshot.indicators.get("atr", 0.0005)
        sr = detect_sr_levels(snapshot.candles, lookback=50)

        is_rejection, rej_dir, level = check_sr_rejection(snapshot.candles[-1], sr, atr)

        if is_rejection and rej_dir != Direction.NO_SIGNAL:
            conf = 0.76
            lvl_type = "Support" if rej_dir == Direction.CALL else "Resistance"
            return StrategyVote(
                strategy_name=self.name,
                direction=rej_dir,
                confidence=conf,
                reasoning=f"Confirmed price rejection at {lvl_type} level {level:.5f}",
                weight=self.weight
            )

        return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "No S/R rejection detected", self.weight)
