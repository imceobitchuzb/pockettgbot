"""
Strategy 6: Momentum Pulse.
Enters on synchronized momentum acceleration across RSI, Stochastic, and Vortex indicators.
"""
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, StrategyVote
from AITradingEngine.strategy_engine.base_strategy import BaseStrategy


class MomentumPulseStrategy(BaseStrategy):
    """Momentum Pulse Strategy."""

    def __init__(self, weight: float = 1.0):
        super().__init__(name="MomentumPulse", weight=weight)

    def evaluate(self, snapshot: MarketSnapshot) -> StrategyVote:
        if not self.is_active:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Strategy inactive", self.weight)

        if snapshot.regime in (MarketRegime.CHOPPY, MarketRegime.UNSTABLE):
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Regime untradable", self.weight)

        ind = snapshot.indicators
        rsi = ind.get("rsi", 50.0)
        stoch_k = ind.get("stoch_k", 50.0)
        stoch_d = ind.get("stoch_d", 50.0)
        roc = ind.get("roc", 0.0)
        vortex_pos = ind.get("vortex_pos", 1.0)
        vortex_neg = ind.get("vortex_neg", 1.0)

        # Bullish Momentum Pulse
        # RSI 50-68 (accelerating upwards), Stoch K crossed above D (<80), ROC > 0, Vortex+ > Vortex-
        if 52.0 <= rsi <= 68.0 and stoch_k > stoch_d and stoch_k < 80.0 and roc > 0.0002 and vortex_pos > vortex_neg:
            conf = 0.74
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.CALL,
                confidence=conf,
                reasoning=f"Bullish momentum alignment (RSI={rsi:.1f}, StochK={stoch_k:.1f}, ROC={roc:.4f}, Vortex+={vortex_pos:.2f})",
                weight=self.weight
            )

        # Bearish Momentum Pulse
        # RSI 32-48 (accelerating downwards), Stoch K crossed below D (>20), ROC < 0, Vortex- > Vortex+
        if 32.0 <= rsi <= 48.0 and stoch_k < stoch_d and stoch_k > 20.0 and roc < -0.0002 and vortex_neg > vortex_pos:
            conf = 0.74
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.PUT,
                confidence=conf,
                reasoning=f"Bearish momentum alignment (RSI={rsi:.1f}, StochK={stoch_k:.1f}, ROC={roc:.4f}, Vortex-={vortex_neg:.2f})",
                weight=self.weight
            )

        return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "No momentum pulse alignment", self.weight)
