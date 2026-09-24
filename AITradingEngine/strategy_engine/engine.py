"""
Strategy Engine Orchestrator.
Executes all 9 independent strategies, gathers point-in-time votes,
and checks for strategy disagreement.
"""
from typing import List, Tuple, Dict, Any
from AITradingEngine.core.enums import Direction
from AITradingEngine.core.models import MarketSnapshot, StrategyVote
from AITradingEngine.strategy_engine.base_strategy import BaseStrategy
from AITradingEngine.strategy_engine.conflict_detector import StrategyConflictDetector
from AITradingEngine.strategy_engine.strategies.s01_trend_following import TrendFollowingStrategy
from AITradingEngine.strategy_engine.strategies.s02_trend_pullback import TrendPullbackStrategy
from AITradingEngine.strategy_engine.strategies.s03_sr_rejection import SRRejectionStrategy
from AITradingEngine.strategy_engine.strategies.s04_breakout_confirm import BreakoutConfirmStrategy
from AITradingEngine.strategy_engine.strategies.s05_false_breakout import FalseBreakoutStrategy
from AITradingEngine.strategy_engine.strategies.s06_momentum_pulse import MomentumPulseStrategy
from AITradingEngine.strategy_engine.strategies.s07_mean_reversion import MeanReversionStrategy
from AITradingEngine.strategy_engine.strategies.s08_volatility_regime import VolatilityRegimeStrategy
from AITradingEngine.strategy_engine.strategies.s09_mtf_confluence import MTFConfluenceStrategy


class StrategyEngine:
    """Manages and executes all 9 independent trading strategies."""

    def __init__(self):
        self.strategies: List[BaseStrategy] = [
            TrendFollowingStrategy(),
            TrendPullbackStrategy(),
            SRRejectionStrategy(),
            BreakoutConfirmStrategy(),
            FalseBreakoutStrategy(),
            MomentumPulseStrategy(),
            MeanReversionStrategy(),
            VolatilityRegimeStrategy(),
            MTFConfluenceStrategy()
        ]
        self.conflict_detector = StrategyConflictDetector(min_confidence_threshold=0.65)

    def evaluate_all(
        self,
        snapshot: MarketSnapshot
    ) -> Tuple[Direction, List[StrategyVote], bool, str]:
        """
        Runs all strategies on the snapshot.
        Returns: (aggregate_direction, all_votes, has_conflict, conflict_message)
        """
        votes: List[StrategyVote] = []
        for strat in self.strategies:
            try:
                vote = strat.evaluate(snapshot)
                votes.append(vote)
            except Exception as e:
                votes.append(StrategyVote(strat.name, Direction.NO_SIGNAL, 0.0, f"Error: {e}", strat.weight))

        # Check for directional conflict
        has_conflict, conflict_msg, _ = self.conflict_detector.detect_conflict(votes)
        if has_conflict:
            return Direction.NO_SIGNAL, votes, True, conflict_msg

        # Filter active positive votes
        call_weight = sum(v.weight * v.confidence for v in votes if v.direction == Direction.CALL)
        put_weight = sum(v.weight * v.confidence for v in votes if v.direction == Direction.PUT)

        min_weight_threshold = 1.3  # At least 1 strong weighted vote or 2 supporting votes

        if call_weight > put_weight and call_weight >= min_weight_threshold:
            return Direction.CALL, votes, False, ""
        elif put_weight > call_weight and put_weight >= min_weight_threshold:
            return Direction.PUT, votes, False, ""

        return Direction.NO_SIGNAL, votes, False, "Insufficient strategy consensus"
