"""
Strategy 2: Trend Pullback.
Enters on pullback to dynamic support/resistance (EMA 21/50) within an established trend.
"""
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, StrategyVote
from AITradingEngine.strategy_engine.base_strategy import BaseStrategy
from AITradingEngine.pattern_engine.price_action import detect_pin_bar


class TrendPullbackStrategy(BaseStrategy):
    """Trend Pullback Strategy."""

    def __init__(self, weight: float = 1.15):
        super().__init__(name="TrendPullback", weight=weight)

    def evaluate(self, snapshot: MarketSnapshot) -> StrategyVote:
        if not self.is_active:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Strategy inactive", self.weight)

        if snapshot.regime not in (MarketRegime.TREND_UP, MarketRegime.TREND_DOWN):
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Market not in clear trending regime", self.weight)

        ind = snapshot.indicators
        e21 = ind.get("ema21", 0.0)
        e50 = ind.get("ema50", 0.0)
        atr = ind.get("atr", 0.0005)
        stoch_k = ind.get("stoch_k", 50.0)
        stoch_d = ind.get("stoch_d", 50.0)

        if len(snapshot.candles) < 2:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Insufficient candles", self.weight)

        curr = snapshot.candles[-1]
        is_pin, pin_dir = detect_pin_bar(curr, atr)
        tolerance = 1.2 * atr if atr > 0 else 0.0004

        # Uptrend Pullback:
        # e21 > e50, price touched near e21 (low touched or close near e21), candle closed green or pin bar
        if snapshot.regime == MarketRegime.TREND_UP and e21 > e50:
            pulled_back = abs(curr.low - e21) <= tolerance or abs(curr.low - e50) <= tolerance
            rebounding = curr.close > curr.open or pin_dir == Direction.CALL
            oversold_rebound = stoch_k < 45.0 and stoch_k > stoch_d

            if pulled_back and (rebounding or oversold_rebound):
                conf = 0.72 + (0.1 if pin_dir == Direction.CALL else 0.0)
                return StrategyVote(
                    strategy_name=self.name,
                    direction=Direction.CALL,
                    confidence=round(conf, 3),
                    reasoning=f"Bullish pullback to EMA 21 ({e21:.5f}) with bounce, StochK={stoch_k:.1f}",
                    weight=self.weight
                )

        # Downtrend Pullback:
        # e21 < e50, price touched near e21 (high touched or close near e21), candle closed red or pin bar
        if snapshot.regime == MarketRegime.TREND_DOWN and e21 < e50:
            pulled_back = abs(curr.high - e21) <= tolerance or abs(curr.high - e50) <= tolerance
            rebounding = curr.close < curr.open or pin_dir == Direction.PUT
            overbought_rebound = stoch_k > 55.0 and stoch_k < stoch_d

            if pulled_back and (rebounding or overbought_rebound):
                conf = 0.72 + (0.1 if pin_dir == Direction.PUT else 0.0)
                return StrategyVote(
                    strategy_name=self.name,
                    direction=Direction.PUT,
                    confidence=round(conf, 3),
                    reasoning=f"Bearish pullback to EMA 21 ({e21:.5f}) with rejection, StochK={stoch_k:.1f}",
                    weight=self.weight
                )

        return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "No clear trend pullback setup", self.weight)
