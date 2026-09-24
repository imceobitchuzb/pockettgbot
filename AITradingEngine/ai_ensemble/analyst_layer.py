"""
AI Layer #1: Market Analyst.
Synthesizes technical indicators, market snapshot, and strategy votes to construct
a comprehensive trade thesis with identified confluence tags.
"""
from typing import List, Dict, Any, Tuple
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, StrategyVote


class AnalystLayer:
    """AI #1 Analyst generating initial trade hypotheses."""

    def __init__(self):
        pass

    def analyze(
        self,
        snapshot: MarketSnapshot,
        strategy_votes: List[StrategyVote],
        dominant_direction: Direction
    ) -> Dict[str, Any]:
        """
        Builds trade hypothesis and gathers confluence factors.
        Returns thesis dictionary.
        """
        if dominant_direction == Direction.NO_SIGNAL:
            return {
                "has_thesis": False,
                "direction": Direction.NO_SIGNAL,
                "confluence_tags": [],
                "confluence_count": 0,
                "setup_name": "NONE",
                "raw_confidence": 0.0,
                "rationale": "No dominant directional setup identified"
            }

        confluence_tags: List[str] = []
        ind = snapshot.indicators

        # 1. Check Trend Confluence
        if dominant_direction == Direction.CALL and snapshot.regime == MarketRegime.TREND_UP:
            confluence_tags.append("Trend Alignment")
        elif dominant_direction == Direction.PUT and snapshot.regime == MarketRegime.TREND_DOWN:
            confluence_tags.append("Trend Alignment")

        # 2. Check MTF Confluence
        if snapshot.mtf_alignment and not snapshot.mtf_alignment.has_conflict:
            if snapshot.mtf_alignment.macro_trend == dominant_direction:
                confluence_tags.append("MTF Macro Alignment")
            if snapshot.mtf_alignment.concordance_score >= 0.75:
                confluence_tags.append("High MTF Concordance")

        # 3. Check Momentum Confluence
        rsi = ind.get("rsi", 50.0)
        if dominant_direction == Direction.CALL and (45.0 <= rsi <= 68.0 or rsi < 30.0):
            confluence_tags.append("Momentum Room / Rebound")
        elif dominant_direction == Direction.PUT and (32.0 <= rsi <= 55.0 or rsi > 70.0):
            confluence_tags.append("Momentum Room / Rebound")

        # 4. Check Strategy Votes Confluence
        active_supporting_votes = [
            v for v in strategy_votes
            if v.direction == dominant_direction and v.confidence >= 0.70
        ]
        if len(active_supporting_votes) >= 2:
            confluence_tags.append(f"Multi-Strategy Consensus ({len(active_supporting_votes)} votes)")

        # 5. Check Structure Confluence
        struct = ind.get("structure", "NEUTRAL")
        if (dominant_direction == Direction.CALL and "BULLISH" in struct) or \
           (dominant_direction == Direction.PUT and "BEARISH" in struct):
            confluence_tags.append("Price Structure")

        # Find primary setup name
        primary_setup = active_supporting_votes[0].strategy_name if active_supporting_votes else "QUANT_MOMENTUM"

        # Calculate base raw confidence
        base_conf = sum(v.confidence for v in active_supporting_votes) / max(len(active_supporting_votes), 1)
        bonus = min(0.15, len(confluence_tags) * 0.03)
        raw_conf = min(0.95, base_conf + bonus)

        return {
            "has_thesis": True,
            "direction": dominant_direction,
            "confluence_tags": confluence_tags,
            "confluence_count": len(confluence_tags),
            "setup_name": primary_setup,
            "raw_confidence": round(raw_conf, 3),
            "rationale": f"Analyst thesis formulated for {dominant_direction.value} based on {len(confluence_tags)} confluence factors."
        }
