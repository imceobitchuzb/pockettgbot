"""
Concept Drift Detector.
Monitors strategy live win rates over a rolling window.
Automatically flags and suspends strategies when performance drifts below the breakeven threshold.
"""
from typing import Dict, List, Any


class ConceptDriftDetector:
    """Detects alpha decay and concept drift in live strategy outputs."""

    def __init__(
        self,
        window_size: int = 30,
        breakeven_win_rate: float = 54.1,
        suspension_threshold: float = 52.0
    ):
        self.window_size = window_size
        self.breakeven_win_rate = breakeven_win_rate
        self.suspension_threshold = suspension_threshold

        # Map: strategy_name -> list of recent outcomes (1 for Win, 0 for Loss)
        self._strategy_history: Dict[str, List[int]] = {}
        self._suspended_strategies: Dict[str, str] = {}

    def record_trade_outcome(self, strategy_name: str, is_win: bool) -> Dict[str, Any]:
        """
        Records verified outcome for a strategy and evaluates concept drift.
        """
        if strategy_name not in self._strategy_history:
            self._strategy_history[strategy_name] = []

        history = self._strategy_history[strategy_name]
        history.append(1 if is_win else 0)

        # Trim to window
        if len(history) > self.window_size:
            history.pop(0)

        # Evaluate drift if we have at least 15 trades
        if len(history) >= 15:
            wins = sum(history)
            rolling_wr = (wins / len(history)) * 100.0

            if rolling_wr < self.suspension_threshold:
                reason = f"Concept drift detected: Rolling WR {rolling_wr:.1f}% < threshold {self.suspension_threshold}%"
                self._suspended_strategies[strategy_name] = reason
                return {
                    "strategy": strategy_name,
                    "is_suspended": True,
                    "rolling_wr": round(rolling_wr, 1),
                    "reason": reason
                }
            else:
                # If was suspended and recovered above breakeven
                if strategy_name in self._suspended_strategies and rolling_wr >= self.breakeven_win_rate:
                    del self._suspended_strategies[strategy_name]

        return {
            "strategy": strategy_name,
            "is_suspended": strategy_name in self._suspended_strategies,
            "rolling_wr": round((sum(history) / len(history)) * 100.0, 1) if history else 0.0,
            "sample_size": len(history)
        }

    def is_suspended(self, strategy_name: str) -> bool:
        """Checks if a strategy is currently suspended due to concept drift."""
        return strategy_name in self._suspended_strategies

    def get_suspended_strategies(self) -> Dict[str, str]:
        """Returns all currently suspended strategies with reasons."""
        return dict(self._suspended_strategies)
