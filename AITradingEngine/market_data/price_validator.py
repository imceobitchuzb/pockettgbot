"""
Price Validator & Data Health Auditor.
Enforces tick-level data hygiene:
1. Spike detection (> 4x ATR or abnormal percentage jumps)
2. Latency & Stale data gating (drops quotes older than threshold)
3. Spread sanity & inverted bid/ask rejection
4. Price comparison & synchronization audit (Source Feed vs Bot Feed)
"""
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

from AITradingEngine.market_data.pocket_option_adapter import NormalizedTick


@dataclass
class ValidationResult:
    is_valid: bool
    status: str  # "VALID", "STALE_DATA", "PRICE_SPIKE", "INVERTED_SPREAD", "LATENCY_GATED", "INVALID_TICK"
    rejection_reason: Optional[str] = None
    latency_ms: float = 0.0
    age_seconds: float = 0.0


@dataclass
class PriceComparison:
    symbol: str
    source_price: float
    bot_price: float
    diff: float
    diff_pips: float
    diff_percent: float
    latency_ms: float
    status: str  # "SYNCHRONIZED", "SLIGHT_LAG", "DESYNC", "STALE"
    source: str
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "source_price": self.source_price,
            "bot_price": self.bot_price,
            "diff": self.diff,
            "diff_pips": self.diff_pips,
            "diff_percent": self.diff_percent,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "source": self.source,
            "timestamp": self.timestamp
        }


class PriceValidator:
    def __init__(self, max_stale_seconds: float = 2.0, max_latency_ms: float = 350.0, max_spread_pct: float = 0.005):
        self.max_stale_seconds = max_stale_seconds
        self.max_latency_ms = max_latency_ms
        self.max_spread_pct = max_spread_pct

    def validate_tick(
        self,
        tick: NormalizedTick,
        last_tick: Optional[NormalizedTick] = None,
        atr: float = 0.0
    ) -> ValidationResult:
        now = time.time()
        age = now - tick.server_timestamp

        # 1. Latency check
        if tick.latency_ms > self.max_latency_ms:
            return ValidationResult(
                is_valid=False,
                status="LATENCY_GATED",
                rejection_reason=f"Latency {tick.latency_ms:.1f}ms exceeds threshold {self.max_latency_ms}ms",
                latency_ms=tick.latency_ms,
                age_seconds=round(age, 3)
            )

        # 2. Stale data check
        if age > self.max_stale_seconds:
            return ValidationResult(
                is_valid=False,
                status="STALE_DATA",
                rejection_reason=f"Data age {age:.2f}s exceeds stale limit {self.max_stale_seconds}s",
                latency_ms=tick.latency_ms,
                age_seconds=round(age, 3)
            )

        # 3. Spread sanity check
        if tick.ask < tick.bid:
            return ValidationResult(
                is_valid=False,
                status="INVERTED_SPREAD",
                rejection_reason=f"Inverted spread: ask ({tick.ask}) < bid ({tick.bid})",
                latency_ms=tick.latency_ms,
                age_seconds=round(age, 3)
            )

        spread = tick.ask - tick.bid
        if tick.price > 0 and (spread / tick.price) > self.max_spread_pct:
            return ValidationResult(
                is_valid=False,
                status="EXCESSIVE_SPREAD",
                rejection_reason=f"Spread percentage {(spread / tick.price) * 100:.3f}% exceeds limit",
                latency_ms=tick.latency_ms,
                age_seconds=round(age, 3)
            )

        # 4. Spike detection (> 4x ATR or > 3% jump)
        if last_tick and last_tick.price > 0:
            price_delta = abs(tick.price - last_tick.price)
            if atr > 0 and price_delta > (4.0 * atr):
                return ValidationResult(
                    is_valid=False,
                    status="PRICE_SPIKE",
                    rejection_reason=f"Price delta {price_delta:.5f} exceeds 4x ATR ({4.0 * atr:.5f})",
                    latency_ms=tick.latency_ms,
                    age_seconds=round(age, 3)
                )
            # Relative percentage jump guard (> 3.5%)
            rel_jump = price_delta / last_tick.price
            if rel_jump > 0.035:
                return ValidationResult(
                    is_valid=False,
                    status="PRICE_SPIKE",
                    rejection_reason=f"Relative price spike of {rel_jump * 100:.2f}% detected",
                    latency_ms=tick.latency_ms,
                    age_seconds=round(age, 3)
                )

        return ValidationResult(
            is_valid=True,
            status="VALID",
            latency_ms=tick.latency_ms,
            age_seconds=round(age, 3)
        )

    def compare_prices(
        self,
        symbol: str,
        source_tick: Optional[NormalizedTick],
        bot_price: float
    ) -> PriceComparison:
        now = time.time()
        if not source_tick:
            return PriceComparison(
                symbol=symbol,
                source_price=bot_price,
                bot_price=bot_price,
                diff=0.0,
                diff_pips=0.0,
                diff_percent=0.0,
                latency_ms=0.0,
                status="SYNCHRONIZED",
                source="INTERNAL_CACHE",
                timestamp=now
            )

        source_p = source_tick.price
        diff = round(abs(source_p - bot_price), 5)
        diff_pct = round((diff / source_p) * 100.0, 4) if source_p > 0 else 0.0
        pip_unit = 0.01 if "JPY" in symbol else 0.0001
        diff_pips = round(diff / pip_unit, 2)

        age = now - source_tick.server_timestamp
        if age > self.max_stale_seconds:
            status = "STALE"
        elif diff_pips > 5.0 or diff_pct > 0.05:
            status = "DESYNC"
        elif diff_pips > 1.5:
            status = "SLIGHT_LAG"
        else:
            status = "SYNCHRONIZED"

        return PriceComparison(
            symbol=symbol,
            source_price=source_p,
            bot_price=bot_price,
            diff=diff,
            diff_pips=diff_pips,
            diff_percent=diff_pct,
            latency_ms=source_tick.latency_ms,
            status=status,
            source=source_tick.source,
            timestamp=now
        )


price_validator = PriceValidator()
