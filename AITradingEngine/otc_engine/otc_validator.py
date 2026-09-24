"""
OTC Market Validator & Environment.
Specialized logic for Pocket Option Over-The-Counter (OTC) instruments:
- Operates 24/7 (including weekends).
- Heightened sensitivity to synthetic micro-clusters and broker payout fluctuations.
- Enforces strict OTC isolation.
"""
from typing import Tuple, Dict, Any
from AITradingEngine.core.enums import MarketType
from AITradingEngine.core.models import MarketSnapshot


class OTCValidator:
    """Validates conditions unique to OTC markets."""

    def __init__(self, min_otc_payout: float = 0.85):
        self.min_otc_payout = min_otc_payout

    def validate_otc_environment(self, snapshot: MarketSnapshot) -> Tuple[bool, str]:
        """
        Validates whether OTC snapshot is structurally sound for trading.
        """
        if snapshot.market_type != MarketType.OTC:
            return False, "Not an OTC asset"

        if snapshot.payout < self.min_otc_payout:
            return False, f"OTC Payout ({int(snapshot.payout * 100)}%) below OTC minimum ({int(self.min_otc_payout * 100)}%)"

        # Check for zero flat candles (synthetic freeze)
        if len(snapshot.candles) >= 5:
            last_5 = snapshot.candles[-5:]
            if all(c.high == c.low for c in last_5):
                return False, "OTC synthetic feed frozen (zero candle range detected)"

        return True, "OTC market environment nominal"
