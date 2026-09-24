"""
Strategy 5: False Breakout (Liquidity Trap / Fakeout).
Enters on confirmed failure of breakout that sweeps liquidity and rejects back into value.
"""
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, StrategyVote
from AITradingEngine.strategy_engine.base_strategy import BaseStrategy
from AITradingEngine.pattern_engine.liquidity import detect_liquidity_sweep, detect_fakeout
from AITradingEngine.pattern_engine.price_action import detect_sr_levels


class FalseBreakoutStrategy(BaseStrategy):
    """False Breakout (Fakeout) Strategy."""

    def __init__(self, weight: float = 1.2):
        super().__init__(name="FalseBreakout", weight=weight)

    def evaluate(self, snapshot: MarketSnapshot) -> StrategyVote:
        if not self.is_active:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Strategy inactive", self.weight)

        if snapshot.regime in (MarketRegime.CHOPPY, MarketRegime.UNSTABLE):
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Regime untradable", self.weight)

        if len(snapshot.candles) < 25:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Insufficient candles", self.weight)

        # 1. Check for liquidity sweep
        is_sweep, sweep_dir, sweep_lvl = detect_liquidity_sweep(snapshot.candles, lookback=20)
        if is_sweep and sweep_dir != Direction.NO_SIGNAL:
            return StrategyVote(
                strategy_name=self.name,
                direction=sweep_dir,
                confidence=0.79,
                reasoning=f"Liquidity sweep detected at {sweep_lvl:.5f} with sharp rejection",
                weight=self.weight
            )

        # 2. Check for S/R fakeout
        sr = detect_sr_levels(snapshot.candles, lookback=40)
        for res in sr.get("resistance", []):
            is_fo, fo_dir = detect_fakeout(snapshot.candles, res, "resistance")
            if is_fo and fo_dir == Direction.PUT:
                return StrategyVote(
                    strategy_name=self.name,
                    direction=Direction.PUT,
                    confidence=0.77,
                    reasoning=f"Bull trap / fakeout above resistance {res:.5f}",
                    weight=self.weight
                )

        for sup in sr.get("support", []):
            is_fo, fo_dir = detect_fakeout(snapshot.candles, sup, "support")
            if is_fo and fo_dir == Direction.CALL:
                return StrategyVote(
                    strategy_name=self.name,
                    direction=Direction.CALL,
                    confidence=0.77,
                    reasoning=f"Bear trap / fakeout below support {sup:.5f}",
                    weight=self.weight
                )

        return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "No false breakout setup", self.weight)
