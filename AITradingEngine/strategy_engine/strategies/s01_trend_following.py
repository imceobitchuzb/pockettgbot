"""
Strategy 1: Trend Following.
Enters strictly in the direction of an established multi-EMA trend confirmed by ADX > 25.
"""
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, StrategyVote
from AITradingEngine.strategy_engine.base_strategy import BaseStrategy


class TrendFollowingStrategy(BaseStrategy):
    """Trend Following Strategy."""

    def __init__(self, weight: float = 1.2):
        super().__init__(name="TrendFollowing", weight=weight)

    def evaluate(self, snapshot: MarketSnapshot) -> StrategyVote:
        if not self.is_active:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Strategy inactive", self.weight)

        # Disallow in choppy or unstable regimes
        if snapshot.regime in (MarketRegime.CHOPPY, MarketRegime.UNSTABLE, MarketRegime.RANGE):
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, f"Incompatible regime: {snapshot.regime.value}", self.weight)

        ind = snapshot.indicators
        adx = ind.get("adx", 0.0)
        p_di = ind.get("plus_di", 0.0)
        m_di = ind.get("minus_di", 0.0)
        e9 = ind.get("ema9", 0.0)
        e21 = ind.get("ema21", 0.0)
        e50 = ind.get("ema50", 0.0)
        rsi = ind.get("rsi", 50.0)
        struct = ind.get("structure", "NEUTRAL")

        # ADX trend threshold
        if adx < 24.0:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, f"ADX too low ({adx:.1f} < 24)", self.weight)

        # Bullish Trend: e9 > e21 > e50, +DI > -DI, Price > e21, RSI between 45 and 70 (not overbought)
        if e9 > e21 > e50 and p_di > m_di and snapshot.current_price > e21 and 45.0 <= rsi <= 72.0:
            conf = min(0.92, 0.65 + (adx / 100.0) * 0.3)
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.CALL,
                confidence=round(conf, 3),
                reasoning=f"Bullish EMA stack (9>21>50), ADX={adx:.1f}, +DI={p_di:.1f}, Structure={struct}",
                weight=self.weight
            )

        # Bearish Trend: e9 < e21 < e50, -DI > +DI, Price < e21, RSI between 28 and 55 (not oversold)
        if e9 < e21 < e50 and m_di > p_di and snapshot.current_price < e21 and 28.0 <= rsi <= 55.0:
            conf = min(0.92, 0.65 + (adx / 100.0) * 0.3)
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.PUT,
                confidence=round(conf, 3),
                reasoning=f"Bearish EMA stack (9<21<50), ADX={adx:.1f}, -DI={m_di:.1f}, Structure={struct}",
                weight=self.weight
            )

        return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Trend criteria not aligned", self.weight)
