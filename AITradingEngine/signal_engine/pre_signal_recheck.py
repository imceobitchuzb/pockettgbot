"""
Pre-Signal Micro Recheck.
Performs an instant sanity check right before signal dispatch to verify that price
has not slipped unfavorably and latency remains within strict limits.
"""
from typing import Tuple
from AITradingEngine.core.enums import Direction


class PreSignalRecheck:
    """Validates real-time price integrity right before dispatch."""

    def __init__(self, max_allowed_slippage_atr_mult: float = 0.5):
        self.max_allowed_slippage_atr_mult = max_allowed_slippage_atr_mult

    def recheck(
        self,
        direction: Direction,
        snapshot_price: float,
        latest_tick_price: float,
        atr: float,
        current_latency_ms: float
    ) -> Tuple[bool, str]:
        """
        Returns (is_valid, reason)
        """
        # 1. Latency check
        if current_latency_ms > 350.0:
            return False, f"Latency spiked ({current_latency_ms:.1f}ms > 350ms)"

        # 2. Price slippage check
        allowed_slippage = self.max_allowed_slippage_atr_mult * atr if atr > 0 else 0.0003

        if direction == Direction.CALL:
            # If price spiked upwards significantly already, entry is chased/unfavorable
            if (latest_tick_price - snapshot_price) > allowed_slippage:
                return False, f"Price ran ahead ({latest_tick_price - snapshot_price:.5f} > {allowed_slippage:.5f}) - entry invalidated"

        elif direction == Direction.PUT:
            # If price dumped downwards significantly already, entry is chased/unfavorable
            if (snapshot_price - latest_tick_price) > allowed_slippage:
                return False, f"Price dropped ahead ({snapshot_price - latest_tick_price:.5f} > {allowed_slippage:.5f}) - entry invalidated"

        return True, "Pre-signal recheck passed"
