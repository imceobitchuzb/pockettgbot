"""
Admin Monitoring & Telemetry Engine.
Tracks system-wide health, gate rejection distributions, latency, and performance metrics.
"""
import time
from typing import Dict, Any, List
from AITradingEngine.core.enums import SystemState
from AITradingEngine.database.repository import EngineRepository


class AdminMetricsManager:
    """Aggregates telemetry and quant system metrics for administration."""

    def __init__(self, repository: EngineRepository):
        self.repository = repository
        self.start_time = time.time()

    def get_system_telemetry(
        self,
        current_state: SystemState,
        focus_asset: str = None,
        active_assets_count: int = 0
    ) -> Dict[str, Any]:
        """
        Returns full admin status snapshot.
        """
        uptime_sec = int(time.time() - self.start_time)
        hours = uptime_sec // 3600
        minutes = (uptime_sec % 3600) // 60
        seconds = uptime_sec % 60

        signals = self.repository.get_recent_signals(limit=50)
        rejections = self.repository.get_recent_rejections(limit=50)

        # Count rejections by gate
        gate_counts: Dict[str, int] = {}
        for r in rejections:
            g = r.get("gate_name", "UNKNOWN")
            gate_counts[g] = gate_counts.get(g, 0) + 1

        return {
            "system_state": current_state.value,
            "uptime": f"{hours}h {minutes}m {seconds}s",
            "active_assets_count": active_assets_count,
            "current_focus_asset": focus_asset or "SCANNING_ALL",
            "total_signals_generated": len(signals),
            "total_rejections_logged": len(rejections),
            "rejections_by_gate": gate_counts,
            "recent_signals": signals[:5],
            "recent_rejections": rejections[:5]
        }
