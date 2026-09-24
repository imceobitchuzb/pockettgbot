"""
OTC Performance & Metric Store.
Strictly isolated from Real Market metrics.
"""
from typing import Dict, Any, List
from AITradingEngine.core.enums import MarketType
from AITradingEngine.core.models import FinalSignal


class OTCPerformanceStore:
    """Maintains statistics exclusively for OTC trades."""

    def __init__(self):
        self.market_type = MarketType.OTC
        self.total_signals = 0
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.signals_history: List[FinalSignal] = []

    def record_signal(self, signal: FinalSignal) -> None:
        """Records an OTC signal."""
        assert signal.market_type == MarketType.OTC, "Contamination error: non-OTC signal in OTC store!"
        self.total_signals += 1
        self.signals_history.append(signal)

    def record_outcome(self, signal_id: str, is_win: bool, is_tie: bool = False) -> None:
        """Records verified outcome."""
        if is_tie:
            self.ties += 1
        elif is_win:
            self.wins += 1
        else:
            self.losses += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Returns OTC performance stats."""
        total_resolved = self.wins + self.losses
        win_rate = (self.wins / total_resolved * 100.0) if total_resolved > 0 else 0.0

        return {
            "market_type": "OTC",
            "total_signals": self.total_signals,
            "resolved_trades": total_resolved,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "win_rate": round(win_rate, 2)
        }
