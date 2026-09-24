"""
Opportunity Queue.
Maintains a dynamically sorted queue of trading assets prioritized by market quality score.
If no instrument satisfies institutional criteria, provides a clean NO_TRADE state.
"""
from typing import List, Dict, Optional, Tuple
from AITradingEngine.core.models import MarketSnapshot, MarketQualityScore


class OpportunityQueue:
    """Stores and ranks market snapshots by their quality score."""

    def __init__(self, min_tradable_score: float = 65.0):
        self.min_tradable_score = min_tradable_score
        self._ranked_items: List[Tuple[MarketSnapshot, MarketQualityScore]] = []

    def update(self, ranked_items: List[Tuple[MarketSnapshot, MarketQualityScore]]) -> None:
        """Updates and sorts the queue descending by total score."""
        self._ranked_items = sorted(
            ranked_items,
            key=lambda x: x[1].total_score,
            reverse=True
        )

    def get_top_candidate(self) -> Optional[Tuple[MarketSnapshot, MarketQualityScore]]:
        """Returns the single highest quality asset snapshot, or None if no asset is tradable."""
        if not self._ranked_items:
            return None

        best_snapshot, best_score = self._ranked_items[0]
        if best_score.is_tradable and best_score.total_score >= self.min_tradable_score:
            return best_snapshot, best_score

        return None

    def get_tradable_candidates(self) -> List[Tuple[MarketSnapshot, MarketQualityScore]]:
        """Returns all assets that currently pass tradability criteria."""
        return [
            (snap, score) for snap, score in self._ranked_items
            if score.is_tradable and score.total_score >= self.min_tradable_score
        ]

    def get_all_ranked(self) -> List[Tuple[MarketSnapshot, MarketQualityScore]]:
        """Returns all tracked assets in ranked order."""
        return list(self._ranked_items)

    def is_any_market_tradable(self) -> bool:
        """Zero-forced-signal helper: check if any market is worth trading right now."""
        return any(score.is_tradable for _, score in self._ranked_items)
