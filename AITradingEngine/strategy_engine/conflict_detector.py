"""
Strategy Disagreement & Conflict Detector.
Enforces institutional discipline: If strategy models disagree on direction,
the trade setup is immediately flagged as conflicted and rejected (NO_TRADE).
"""
from typing import List, Tuple, Dict, Any
from AITradingEngine.core.enums import Direction
from AITradingEngine.core.models import StrategyVote


class StrategyConflictDetector:
    """Detects opposing directional votes among independent strategies."""

    def __init__(self, min_confidence_threshold: float = 0.65):
        self.min_confidence_threshold = min_confidence_threshold

    def detect_conflict(self, votes: List[StrategyVote]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates votes for directional conflict.
        Returns: (has_conflict, description, details)
        """
        call_votes = [
            v for v in votes
            if v.direction == Direction.CALL and v.confidence >= self.min_confidence_threshold
        ]
        put_votes = [
            v for v in votes
            if v.direction == Direction.PUT and v.confidence >= self.min_confidence_threshold
        ]

        details = {
            "call_count": len(call_votes),
            "put_count": len(put_votes),
            "calling_strategies": [v.strategy_name for v in call_votes],
            "putting_strategies": [v.strategy_name for v in put_votes]
        }

        # If we have both active CALL and PUT votes, flag strict conflict
        if call_votes and put_votes:
            call_names = ", ".join(v.strategy_name for v in call_votes)
            put_names = ", ".join(v.strategy_name for v in put_votes)
            msg = f"Directional Conflict: [{call_names}] vote CALL vs [{put_names}] vote PUT"
            return True, msg, details

        return False, "No directional conflict detected", details
