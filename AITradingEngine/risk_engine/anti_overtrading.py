"""
Anti-Overtrading Module.
Prevents rapid trade spam, duplicate entries on the same asset, and enforces cooldown windows.
"""
import time
from typing import Dict, Optional, Tuple


class AntiOvertradingEngine:
    """Guards against overtrading and rapid successive entries."""

    def __init__(
        self,
        asset_cooldown_seconds: float = 180.0,
        max_signals_per_hour: int = 6
    ):
        self.asset_cooldown_seconds = asset_cooldown_seconds
        self.max_signals_per_hour = max_signals_per_hour

        self._last_signal_time: Dict[str, float] = {}
        self._signal_history_timestamps: list[float] = []

    def check_trade_allowed(self, symbol: str) -> Tuple[bool, str]:
        """
        Validates if a new trade can be issued for symbol right now.
        Returns: (is_allowed, reason)
        """
        now = time.time()

        # 1. Clean history older than 1 hour (3600 sec)
        self._signal_history_timestamps = [ts for ts in self._signal_history_timestamps if (now - ts) < 3600]

        # 2. Check global hourly rate limit
        if len(self._signal_history_timestamps) >= self.max_signals_per_hour:
            return False, f"Hourly signal limit reached ({len(self._signal_history_timestamps)}/{self.max_signals_per_hour})"

        # 3. Check per-symbol cooldown
        last_time = self._last_signal_time.get(symbol, 0.0)
        elapsed = now - last_time
        if elapsed < self.asset_cooldown_seconds:
            remaining = int(self.asset_cooldown_seconds - elapsed)
            return False, f"Asset cooldown active for {symbol} ({remaining}s remaining)"

        return True, "Trading allowed"

    def record_signal(self, symbol: str) -> None:
        """Records dispatched signal timestamp."""
        now = time.time()
        self._last_signal_time[symbol] = now
        self._signal_history_timestamps.append(now)
