"""
Base Strategy Interface for Quant Signal Engine.
Every strategy must implement evaluate() returning a StrategyVote.
"""
from abc import ABC, abstractmethod
from AITradingEngine.core.models import MarketSnapshot, StrategyVote


class BaseStrategy(ABC):
    """Abstract Base Class for all trading strategies."""

    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight
        self.is_active = True

    @abstractmethod
    def evaluate(self, snapshot: MarketSnapshot) -> StrategyVote:
        """
        Evaluates current snapshot point-in-time.
        Must return StrategyVote with direction, confidence (0.0 to 1.0), and reasoning.
        """
        pass
