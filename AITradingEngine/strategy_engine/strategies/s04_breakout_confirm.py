"""
Strategy 4: Breakout Confirmation.
Enters on confirmed breakout of key support/resistance levels with momentum acceleration.
"""
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, StrategyVote
from AITradingEngine.strategy_engine.base_strategy import BaseStrategy
from AITradingEngine.pattern_engine.price_action import detect_sr_levels


class BreakoutConfirmStrategy(BaseStrategy):
    """Breakout Confirmation Strategy."""

    def __init__(self, weight: float = 1.05):
        super().__init__(name="BreakoutConfirm", weight=weight)

    def evaluate(self, snapshot: MarketSnapshot) -> StrategyVote:
        if not self.is_active:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Strategy inactive", self.weight)

        if snapshot.regime in (MarketRegime.CHOPPY, MarketRegime.UNSTABLE, MarketRegime.RANGE):
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Regime not suitable for breakout", self.weight)

        if len(snapshot.candles) < 20:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Insufficient candles", self.weight)

        sr = detect_sr_levels(snapshot.candles[:-1], lookback=40)
        curr = snapshot.candles[-1]
        prev = snapshot.candles[-2]
        ind = snapshot.indicators
        roc = ind.get("roc", 0.0)
        bb_upper = ind.get("bb_upper", 0.0)
        bb_lower = ind.get("bb_lower", 0.0)

        # Bullish Breakout: Candle closed convincingly above resistance level with positive momentum
        for res in sr.get("resistance", []):
            if prev.close <= res and curr.close > res:
                body = curr.close - curr.open
                if body > 0 and roc > 0:
                    return StrategyVote(
                        strategy_name=self.name,
                        direction=Direction.CALL,
                        confidence=0.74,
                        reasoning=f"Confirmed bullish breakout above resistance {res:.5f} with ROC={roc:.3f}",
                        weight=self.weight
                    )

        # Bearish Breakout: Candle closed convincingly below support level with negative momentum
        for sup in sr.get("support", []):
            if prev.close >= sup and curr.close < sup:
                body = curr.open - curr.close
                if body > 0 and roc < 0:
                    return StrategyVote(
                        strategy_name=self.name,
                        direction=Direction.PUT,
                        confidence=0.74,
                        reasoning=f"Confirmed bearish breakout below support {sup:.5f} with ROC={roc:.3f}",
                        weight=self.weight
                    )

        return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "No breakout confirmation", self.weight)
