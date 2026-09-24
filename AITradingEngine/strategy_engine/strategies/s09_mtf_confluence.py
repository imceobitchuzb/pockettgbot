"""
Strategy 9: Multi-Timeframe Confluence.
Enters strictly when 5m Macro, 1m Structure, and Entry timeframes all show unified directional alignment.
"""
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, StrategyVote
from AITradingEngine.strategy_engine.base_strategy import BaseStrategy


class MTFConfluenceStrategy(BaseStrategy):
    """Multi-Timeframe Confluence Strategy."""

    def __init__(self, weight: float = 1.3):
        super().__init__(name="MTFConfluence", weight=weight)

    def evaluate(self, snapshot: MarketSnapshot) -> StrategyVote:
        if not self.is_active:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Strategy inactive", self.weight)

        mtf = snapshot.mtf_alignment
        if not mtf:
            return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "No MTF data available", self.weight)

        # Disagreement between timeframes -> STRICT NO TRADE
        if mtf.has_conflict:
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.NO_SIGNAL,
                confidence=0.0,
                reasoning=f"MTF conflict: Macro={mtf.macro_trend.value}, Structure={mtf.structure_trend.value}, Entry={mtf.entry_trend.value}",
                weight=self.weight
            )

        # Full Concordance Bullish
        if (
            mtf.macro_trend == Direction.CALL and
            mtf.structure_trend == Direction.CALL and
            mtf.entry_trend == Direction.CALL and
            mtf.concordance_score >= 0.8
        ):
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.CALL,
                confidence=0.82,
                reasoning=f"Full MTF Bullish Concordance (Score: {mtf.concordance_score:.2f}) across 5m, 1m, entry",
                weight=self.weight
            )

        # Full Concordance Bearish
        if (
            mtf.macro_trend == Direction.PUT and
            mtf.structure_trend == Direction.PUT and
            mtf.entry_trend == Direction.PUT and
            mtf.concordance_score >= 0.8
        ):
            return StrategyVote(
                strategy_name=self.name,
                direction=Direction.PUT,
                confidence=0.82,
                reasoning=f"Full MTF Bearish Concordance (Score: {mtf.concordance_score:.2f}) across 5m, 1m, entry",
                weight=self.weight
            )

        return StrategyVote(self.name, Direction.NO_SIGNAL, 0.0, "Timeframes not in full alignment", self.weight)
