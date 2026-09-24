"""
Uncertainty Engine.
Quantifies market and model uncertainty to protect against distribution shifts and noisy regimes.
"""
from typing import Dict, Any, List
from AITradingEngine.core.models import MarketSnapshot, StrategyVote


class UncertaintyEngine:
    """Estimates epistemic and aleatoric uncertainty of trade setups."""

    def __init__(self, max_uncertainty_threshold: float = 0.35):
        self.max_uncertainty_threshold = max_uncertainty_threshold

    def calculate_uncertainty(
        self,
        snapshot: MarketSnapshot,
        votes: List[StrategyVote],
        analyst_conf: float
    ) -> Dict[str, Any]:
        """
        Calculates composite uncertainty score (0.0 to 1.0).
        Lower is better/more certain.
        """
        # 1. Variance in strategy votes
        active_confs = [v.confidence for v in votes if v.confidence > 0]
        if active_confs:
            mean_conf = sum(active_confs) / len(active_confs)
            variance = sum((c - mean_conf) ** 2 for c in active_confs) / len(active_confs)
            vote_dispersion = min(0.4, variance * 4.0)
        else:
            vote_dispersion = 0.3

        # 2. Indicator noise uncertainty
        ind = snapshot.indicators
        bw = ind.get("bb_bandwidth", 0.002)
        # Squeezes or extreme expansions have higher volatility uncertainty
        vol_uncertainty = 0.15 if ind.get("bb_is_squeeze", False) else 0.05

        # 3. MTF uncertainty
        mtf_uncertainty = 0.2 if (not snapshot.mtf_alignment or snapshot.mtf_alignment.has_conflict) else 0.0

        total_uncertainty = round(vote_dispersion + vol_uncertainty + mtf_uncertainty, 3)
        is_vetoed = total_uncertainty > self.max_uncertainty_threshold

        return {
            "uncertainty_score": total_uncertainty,
            "is_vetoed": is_vetoed,
            "reason": f"High uncertainty ({total_uncertainty} > {self.max_uncertainty_threshold})" if is_vetoed else "Acceptable uncertainty"
        }
