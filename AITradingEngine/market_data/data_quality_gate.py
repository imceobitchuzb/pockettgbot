"""
Data Quality Gate.
Enforces institutional mathematical integrity on all candlestick series and market snapshots.
Rejects any corrupted, stale, gapped, or manipulated market data before reaching the analytics engine.
Returns PASS, WARN, FAIL verdicts. If FAIL => mandatory NO TRADE.
"""
import math
import time
from enum import Enum
from typing import List, Dict, Any, Optional

from AITradingEngine.core.models import Candle


class QualityVerdict(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class DataQualityGateResult:
    def __init__(self, verdict: QualityVerdict, score: float, reasons: List[str], details: Dict[str, Any]):
        self.verdict = verdict
        self.score = round(score, 2)  # 0.0 to 100.0
        self.reasons = reasons
        self.details = details
        self.is_passed = (verdict == QualityVerdict.PASS)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "score": self.score,
            "reasons": self.reasons,
            "details": self.details,
            "is_passed": self.is_passed
        }

    def __repr__(self) -> str:
        return f"DataQualityGateResult({self.verdict.value}, score={self.score}, reasons={self.reasons})"


class DataQualityGate:
    """Pre-analytics validation gate for candlestick series and real-time quotes."""

    def __init__(
        self,
        min_candles: int = 30,
        max_age_seconds: float = 300.0,
        max_jump_percent: float = 8.0,
        max_gap_seconds: int = 360
    ):
        self.min_candles = min_candles
        self.max_age_seconds = max_age_seconds
        self.max_jump_percent = max_jump_percent
        self.max_gap_seconds = max_gap_seconds

    def evaluate(
        self,
        candles: List[Candle],
        current_price: Optional[float] = None,
        last_quote_time: Optional[float] = None,
        expected_timeframe_sec: int = 60
    ) -> DataQualityGateResult:
        reasons: List[str] = []
        details: Dict[str, Any] = {}
        score = 100.0

        # 1. Sufficient History Check
        if not candles or len(candles) < self.min_candles:
            reasons.append(f"Insufficient candle count: {len(candles) if candles else 0}/{self.min_candles}")
            return DataQualityGateResult(QualityVerdict.FAIL, 0.0, reasons, {"candle_count": len(candles) if candles else 0})

        details["candle_count"] = len(candles)

        # 2. Timestamp Freshness Check
        now = time.time()
        newest_candle_time = candles[-1].timestamp
        candle_age = now - newest_candle_time
        details["newest_candle_age_sec"] = round(candle_age, 1)

        if candle_age > self.max_age_seconds:
            reasons.append(f"Candle data is stale (age: {candle_age:.1f}s > {self.max_age_seconds}s)")
            return DataQualityGateResult(QualityVerdict.FAIL, 10.0, reasons, details)

        if last_quote_time is not None:
            quote_age = now - last_quote_time
            details["quote_age_sec"] = round(quote_age, 2)
            if quote_age > 10.0:
                reasons.append(f"Quote stream is stale ({quote_age:.1f}s ago)")
                score -= 25.0

        # 3. Individual Candle OHLC Validity, NaN, and Non-Zero Checks
        seen_timestamps = set()
        prev_time = 0
        prev_close = None

        for idx, c in enumerate(candles):
            # Check for NaN / Inf
            for val_name, val in [("open", c.open), ("high", c.high), ("low", c.low), ("close", c.close)]:
                if val is None or math.isnan(val) or math.isinf(val) or val <= 0:
                    reasons.append(f"Invalid non-positive or NaN {val_name} at index {idx} ({val})")
                    return DataQualityGateResult(QualityVerdict.FAIL, 0.0, reasons, details)

            # High/Low Envelope Integrity
            if c.high < max(c.open, c.close) - 1e-7:
                reasons.append(f"High {c.high} is less than max(open, close) {max(c.open, c.close)} at index {idx}")
                return DataQualityGateResult(QualityVerdict.FAIL, 0.0, reasons, details)

            if c.low > min(c.open, c.close) + 1e-7:
                reasons.append(f"Low {c.low} is greater than min(open, close) {min(c.open, c.close)} at index {idx}")
                return DataQualityGateResult(QualityVerdict.FAIL, 0.0, reasons, details)

            # Duplicate Timestamps
            if c.timestamp in seen_timestamps:
                reasons.append(f"Duplicate candle timestamp {c.timestamp} found at index {idx}")
                return DataQualityGateResult(QualityVerdict.FAIL, 0.0, reasons, details)
            seen_timestamps.add(c.timestamp)

            # Strictly Ascending Order
            if c.timestamp <= prev_time and idx > 0:
                reasons.append(f"Non-monotonic timestamp order at index {idx}: {c.timestamp} <= {prev_time}")
                return DataQualityGateResult(QualityVerdict.FAIL, 0.0, reasons, details)

            # Gap Check
            if idx > 0:
                delta_t = c.timestamp - prev_time
                if delta_t > self.max_gap_seconds:
                    reasons.append(f"Abnormal time gap ({delta_t}s) detected between index {idx-1} and {idx}")
                    score -= 15.0

            # Extreme Jump Check
            if prev_close is not None and prev_close > 0:
                jump_pct = abs(c.open - prev_close) / prev_close * 100.0
                if jump_pct > self.max_jump_percent:
                    reasons.append(f"Unphysical price jump ({jump_pct:.2f}%) at index {idx}")
                    return DataQualityGateResult(QualityVerdict.FAIL, 5.0, reasons, details)

            prev_time = c.timestamp
            prev_close = c.close

        # 4. Consistency of Current Price with Latest Candle
        if current_price is not None and current_price > 0:
            last_bar = candles[-1]
            # Price shouldn't deviate wildly from latest bar range (e.g. within 3% envelope)
            ref = last_bar.close
            dev_pct = abs(current_price - ref) / ref * 100.0
            details["current_price_deviation_pct"] = round(dev_pct, 4)
            if dev_pct > 3.0:
                reasons.append(f"Current price {current_price} deviates {dev_pct:.2f}% from latest closed bar {ref}")
                return DataQualityGateResult(QualityVerdict.FAIL, 15.0, reasons, details)

        score = max(0.0, min(100.0, score))
        verdict = QualityVerdict.PASS if score >= 80.0 and len(reasons) == 0 else (
            QualityVerdict.WARN if score >= 60.0 else QualityVerdict.FAIL
        )

        return DataQualityGateResult(verdict, score, reasons, details)


data_quality_gate = DataQualityGate()
