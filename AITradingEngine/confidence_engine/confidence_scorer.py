"""
Calibrated Confidence Scorer.
Converts raw heuristic/strategy confidence into statistically calibrated probabilities.
Uses Platt/Sigmoid calibration and strictly bounds probabilities to avoid overconfidence.
"""
import math
from typing import Dict, Any


class ConfidenceScorer:
    """Calculates calibrated edge probability for signal candidates."""

    def __init__(
        self,
        min_probability_threshold: float = 0.72,
        max_allowed_probability: float = 0.89  # Strict quant limit: no model can honestly claim >89%
    ):
        self.min_probability_threshold = min_probability_threshold
        self.max_allowed_probability = max_allowed_probability

    def calibrate(
        self,
        raw_confidence: float,
        critic_penalty: float = 0.0,
        uncertainty: float = 0.0
    ) -> float:
        """
        Calibrates raw confidence by penalizing critic findings and uncertainty.
        Applies a sigmoid shrinkage mapping.
        """
        adjusted_raw = max(0.0, raw_confidence - (critic_penalty * 0.5) - (uncertainty * 0.3))

        # Logistic calibration: sigmoid mapping centered around 0.70
        # P = 1 / (1 + exp(-k * (x - x0)))
        x = adjusted_raw
        k = 4.0
        x0 = 0.70
        calibrated = 1.0 / (1.0 + math.exp(-k * (x - x0)))

        # Rescale into realistic binary options probability space [0.50, max_allowed_probability]
        prob = 0.50 + (calibrated * (self.max_allowed_probability - 0.50))

        return round(min(max(prob, 0.50), self.max_allowed_probability), 3)

    def calculate_statistical_edge(self, calibrated_prob: float, payout: float = 0.85) -> Dict[str, Any]:
        """
        Calculates mathematical Expectancy (EV) per $1 risked:
        EV = (P * Payout) - ((1 - P) * 1.0)
        Breakeven win rate at 85% payout is 1 / (1 + 0.85) = 54.05%
        """
        breakeven_wr = 1.0 / (1.0 + payout) if payout > 0 else 0.55
        ev = (calibrated_prob * payout) - ((1.0 - calibrated_prob) * 1.0)
        edge_percent = (calibrated_prob - breakeven_wr) * 100.0

        has_positive_edge = ev > 0.05  # Requires at least +5% expected value

        return {
            "calibrated_probability": calibrated_prob,
            "expected_value": round(ev, 4),
            "edge_percent": round(edge_percent, 2),
            "breakeven_win_rate": round(breakeven_wr, 4),
            "has_positive_edge": has_positive_edge
        }
