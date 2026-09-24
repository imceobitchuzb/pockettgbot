"""
Loss Streak Shield.
Protects capital from adverse regime shifts.
Elevates confidence requirements during drawdown and halts trading after 3 consecutive losses.
ZERO MARTINGALE POLICY: Flat 1.0 unit risk strictly enforced.
"""
import time
from typing import Tuple, Dict, Any


class LossStreakShield:
    """Adaptive risk protection against losing streaks."""

    def __init__(
        self,
        base_confidence_threshold: float = 0.72,
        tightened_confidence_threshold: float = 0.82,
        max_consecutive_losses: int = 3,
        halt_duration_seconds: float = 900.0  # 15 minutes
    ):
        self.base_confidence_threshold = base_confidence_threshold
        self.tightened_confidence_threshold = tightened_confidence_threshold
        self.max_consecutive_losses = max_consecutive_losses
        self.halt_duration_seconds = halt_duration_seconds

        self.consecutive_losses = 0
        self.total_wins = 0
        self.total_losses = 0
        self.halt_until_timestamp: float = 0.0

    def record_outcome(self, is_win: bool) -> None:
        """Updates streak counter based on verified trade outcome."""
        if is_win:
            self.total_wins += 1
            self.consecutive_losses = 0
        else:
            self.total_losses += 1
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.max_consecutive_losses:
                self.halt_until_timestamp = time.time() + self.halt_duration_seconds

    def get_effective_confidence_threshold(self) -> Tuple[float, str]:
        """
        Returns required minimum confidence threshold based on streak status.
        """
        if self.consecutive_losses >= 2:
            return self.tightened_confidence_threshold, f"Tightened due to {self.consecutive_losses} consecutive losses"
        return self.base_confidence_threshold, "Standard risk threshold"

    def is_shield_active(self) -> Tuple[bool, str]:
        """
        Checks if trading is currently halted due to loss streak limit.
        """
        now = time.time()
        if now < self.halt_until_timestamp:
            remaining = int(self.halt_until_timestamp - now)
            return True, f"Trading temporarily paused by Loss Streak Shield ({remaining}s remaining after {self.consecutive_losses} losses)"

        return False, "Loss streak shield inactive"

    def get_status(self) -> Dict[str, Any]:
        """Returns shield telemetry."""
        now = time.time()
        return {
            "consecutive_losses": self.consecutive_losses,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "is_halted": now < self.halt_until_timestamp,
            "seconds_remaining": max(0, int(self.halt_until_timestamp - now))
        }
