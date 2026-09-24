"""
Emergency Circuit Breaker.
Provides automated kill-switch mechanics if system metrics, API health,
or account drawdown exceed critical institutional safety thresholds.
"""
from typing import Tuple, Dict, Any


class EmergencyShutdownEngine:
    """System-level circuit breaker and safety kill-switch."""

    def __init__(
        self,
        max_daily_drawdown_pct: float = 15.0,
        max_api_error_rate_pct: float = 20.0
    ):
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.max_api_error_rate_pct = max_api_error_rate_pct

        self._is_tripped = False
        self._trip_reason: str = ""
        self._manual_emergency_stop = False

    def trigger_emergency_stop(self, reason: str = "Manual Admin Emergency Stop") -> None:
        """Manually shuts down engine."""
        self._is_tripped = True
        self._manual_emergency_stop = True
        self._trip_reason = reason

    def reset_circuit_breaker(self) -> None:
        """Resets the circuit breaker."""
        self._is_tripped = False
        self._manual_emergency_stop = False
        self._trip_reason = ""

    def evaluate_system_health(
        self,
        daily_pnl_pct: float,
        api_error_rate_pct: float
    ) -> Tuple[bool, str]:
        """
        Evaluates real-time health.
        Returns: (is_safe_to_trade, reason)
        """
        if self._is_tripped or self._manual_emergency_stop:
            return False, f"CIRCUIT BREAKER ACTIVE: {self._trip_reason}"

        if daily_pnl_pct <= -self.max_daily_drawdown_pct:
            self._is_tripped = True
            self._trip_reason = f"Max Daily Drawdown exceeded ({daily_pnl_pct:.1f}% <= -{self.max_daily_drawdown_pct}%)"
            return False, self._trip_reason

        if api_error_rate_pct >= self.max_api_error_rate_pct:
            self._is_tripped = True
            self._trip_reason = f"Critical API Error Rate ({api_error_rate_pct:.1f}% >= {self.max_api_error_rate_pct}%)"
            return False, self._trip_reason

        return True, "System health nominal"

    def get_status(self) -> Dict[str, Any]:
        """Returns circuit breaker status."""
        return {
            "is_tripped": self._is_tripped,
            "trip_reason": self._trip_reason,
            "manual_stop": self._manual_emergency_stop
        }
