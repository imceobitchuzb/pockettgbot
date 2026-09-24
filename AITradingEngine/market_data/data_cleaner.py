"""
AITradingEngine Data Cleaner.
Validates integrity of incoming ticks and historical candles.
Rejects data with abnormal price spikes, excessive staleness, or missing intervals.
"""
import time
from typing import List, Tuple, Dict, Any, Optional
from AITradingEngine.core.models import Candle


class DataCleaner:
    def __init__(self, max_staleness_seconds: int = 10, max_spike_multiplier: float = 4.5):
        self.max_staleness = max_staleness_seconds
        self.max_spike_multiplier = max_spike_multiplier

    def validate_candles(self, candles: List[Candle], expected_interval_seconds: int = 60) -> Tuple[bool, List[str]]:
        issues = []
        if not candles or len(candles) < 20:
            return False, ["INSUFFICIENT_HISTORY: Less than 20 candles provided"]

        now = int(time.time())
        last_candle = candles[-1]

        # 1. Staleness check
        staleness = now - last_candle.timestamp
        if staleness > (expected_interval_seconds * 3) and staleness > self.max_staleness:
            issues.append(f"STALE_DATA: Last candle is {staleness}s old (max allowed {expected_interval_seconds * 3}s)")

        # 2. Chronological order and gap check
        gaps_detected = 0
        for i in range(1, len(candles)):
            diff = candles[i].timestamp - candles[i - 1].timestamp
            if diff <= 0:
                issues.append(f"TIMESTAMP_INVERSION_OR_DUPLICATE: Candle {i} at {candles[i].timestamp} <= {candles[i-1].timestamp}")
                break
            if diff > expected_interval_seconds * 3:
                gaps_detected += 1

        if gaps_detected > 2:
            issues.append(f"DATA_GAPS_DETECTED: Found {gaps_detected} missing intervals in recent series")

        # 3. Abnormal price spike (Flash Crash / Bad Tick) detection
        ranges = [c.high - c.low for c in candles[-20:]]
        avg_range = sum(ranges) / len(ranges) if ranges else 0.0001
        if avg_range <= 0:
            avg_range = 0.0001

        last_body = abs(last_candle.close - last_candle.open)
        if last_body > (avg_range * self.max_spike_multiplier):
            issues.append(f"ABNORMAL_PRICE_SPIKE: Candle body ({last_body:.5f}) exceeds {self.max_spike_multiplier}x ATR ({avg_range:.5f})")

        is_valid = len(issues) == 0
        return is_valid, issues

    def validate_tick(self, price: float, last_price: float, max_delta_pct: float = 0.05) -> Tuple[bool, str]:
        if price <= 0:
            return False, "Negative or zero price tick"
        if last_price > 0:
            pct_change = abs(price - last_price) / last_price
            if pct_change > max_delta_pct:
                return False, f"Abnormal tick spike ({pct_change*100:.2f}% > {max_delta_pct*100:.2f}%)"
        return True, "Tick valid"

    def clean_candle_stream(self, candles: List[Candle]) -> List[Candle]:
        if not candles:
            return []
        cleaned = [candles[0]]
        for i in range(1, len(candles)):
            c = candles[i]
            # Must be strictly increasing timestamps
            if c.timestamp > cleaned[-1].timestamp:
                cleaned.append(c)
        return cleaned


data_cleaner = DataCleaner()
validate_tick = data_cleaner.validate_tick
clean_candle_stream = data_cleaner.clean_candle_stream
validate_candles = data_cleaner.validate_candles
