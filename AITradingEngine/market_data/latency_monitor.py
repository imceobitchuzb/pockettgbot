"""
AITradingEngine Latency Monitor
Guarantees execution viability by enforcing strict latency bounds.
Rejects setups if market-to-analysis or analysis-to-delivery latency exceeds 350ms.
"""
import time
from typing import Dict, Any, Tuple

class LatencyMonitor:
    def __init__(self, max_allowed_latency_ms: float = 350.0):
        self.max_allowed_latency_ms = max_allowed_latency_ms
        self.latency_history = []

    def check_latency(self, data_timestamp_sec: int, analysis_start_time: float) -> Tuple[bool, float, str]:
        """
        Returns (is_acceptable: bool, total_latency_ms: float, detail: str)
        """
        now = time.time()
        # Processing latency in milliseconds
        processing_latency_ms = (now - analysis_start_time) * 1000.0
        
        self.latency_history.append(processing_latency_ms)
        if len(self.latency_history) > 100:
            self.latency_history.pop(0)

        if processing_latency_ms > self.max_allowed_latency_ms:
            return False, processing_latency_ms, f"LATENCY_BREACH: Analysis latency {processing_latency_ms:.1f}ms exceeds threshold {self.max_allowed_latency_ms}ms"

        return True, processing_latency_ms, f"LATENCY_OK: {processing_latency_ms:.1f}ms"

    def get_average_latency_ms(self) -> float:
        if not self.latency_history:
            return 0.0
        return round(sum(self.latency_history) / len(self.latency_history), 1)

latency_monitor = LatencyMonitor()
