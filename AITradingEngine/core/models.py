"""
AITradingEngine Core Models.
Unified dataclasses representing market data, analysis snapshots, strategy votes, critic verdicts, and final signals.
Zero look-ahead bias and cross-module compatible.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

from AITradingEngine.core.enums import (
    Direction, MarketType, Timeframe, QualityGrade, MarketRegime, SignalGateResult,
    SignalStrength, SignalLifecycleState
)


class Candle:
    """Represents a point-in-time candle bar."""
    def __init__(
        self,
        timestamp: int,
        open: Optional[float] = None,
        high: Optional[float] = None,
        low: Optional[float] = None,
        close: Optional[float] = None,
        volume: float = 100.0,
        timeframe: Timeframe = Timeframe.M1,
        is_closed: bool = True,
        **kwargs
    ):
        self.timestamp = int(timestamp)
        self.open = float(open if open is not None else kwargs.get("open_p", 0.0))
        self.high = float(high if high is not None else kwargs.get("high_p", 0.0))
        self.low = float(low if low is not None else kwargs.get("low_p", 0.0))
        self.close = float(close if close is not None else kwargs.get("close_p", 0.0))
        self.volume = float(volume)
        self.timeframe = timeframe
        self.is_closed = is_closed

    @property
    def open_p(self) -> float:
        return self.open

    @property
    def high_p(self) -> float:
        return self.high

    @property
    def low_p(self) -> float:
        return self.low

    @property
    def close_p(self) -> float:
        return self.close

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "timeframe": self.timeframe.value if hasattr(self.timeframe, "value") else str(self.timeframe),
            "is_closed": self.is_closed
        }

    def __repr__(self) -> str:
        return f"Candle(t={self.timestamp}, o={self.open:.5f}, h={self.high:.5f}, l={self.low:.5f}, c={self.close:.5f}, tf={self.timeframe})"


class MarketSnapshot:
    """
    Immutable representation of market conditions at timestamp t0.
    Contains strictly closed candles up to t0 (ZERO look-ahead bias).
    """
    def __init__(
        self,
        symbol: Optional[str] = None,
        market_type: MarketType = MarketType.OTC,
        timestamp: Optional[float] = None,
        current_price: float = 0.0,
        primary_timeframe: Timeframe = Timeframe.M1,
        regime: MarketRegime = MarketRegime.UNKNOWN,
        candles: Optional[List[Candle]] = None,
        mtf_candles: Optional[Dict[str, List[Candle]]] = None,
        indicators: Optional[Dict[str, Any]] = None,
        mtf_alignment: Optional[Any] = None,
        payout: float = 0.85,
        **kwargs
    ):
        self.symbol = symbol or kwargs.get("asset", "EUR_USD_OTC")
        self.asset = self.symbol
        self.market_type = market_type
        self.timestamp = timestamp if timestamp is not None else kwargs.get("timestamp", time.time())
        self.current_price = current_price
        self.primary_timeframe = primary_timeframe or kwargs.get("timeframe", Timeframe.M1)
        self.timeframe = self.primary_timeframe
        self.regime = regime or kwargs.get("market_regime", MarketRegime.UNKNOWN)
        self.market_regime = self.regime
        self.candles = candles or []
        self.mtf_candles = mtf_candles or {}
        self.indicators = indicators or {}
        self.mtf_alignment = mtf_alignment
        self.payout = payout
        self.snapshot_id = kwargs.get("snapshot_id", f"{self.symbol}_{int(self.timestamp)}")
        self.volatility_atr = kwargs.get("volatility_atr", self.indicators.get("atr", 0.0))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "symbol": self.symbol,
            "market_type": self.market_type.value,
            "timestamp": self.timestamp,
            "current_price": self.current_price,
            "primary_timeframe": self.primary_timeframe.value,
            "regime": self.regime.value,
            "payout": self.payout,
            "candles_count": len(self.candles),
            "indicators": self.indicators
        }


class StrategyVote:
    """Output from an individual trading strategy."""
    def __init__(
        self,
        strategy_name: str,
        direction: Direction,
        confidence: float,
        reasoning: str = "",
        weight: float = 1.0,
        **kwargs
    ):
        self.strategy_name = strategy_name
        self.direction = direction
        self.confidence = float(confidence)
        self.reasoning = reasoning or "; ".join(kwargs.get("reasons", []))
        self.reasons = [self.reasoning] if self.reasoning else kwargs.get("reasons", [])
        self.weight = float(weight)
        self.setup_quality = kwargs.get("setup_quality", self.confidence)
        self.market_regime = kwargs.get("market_regime", MarketRegime.UNKNOWN)
        self.historical_expectancy = kwargs.get("historical_expectancy", 0.0)
        self.recommended_expiration_sec = kwargs.get("recommended_expiration_sec", 60)

    def __repr__(self) -> str:
        return f"StrategyVote({self.strategy_name}: {self.direction.value} conf={self.confidence:.2f})"


class CriticVerdict:
    """Adversarial evaluation from AI #2 Critic."""
    def __init__(
        self,
        is_approved: bool = True,
        veto_reason: Optional[str] = None,
        penalty_score: float = 0.0,
        risk_notes: str = "",
        **kwargs
    ):
        self.is_approved = is_approved if "approve" not in kwargs else kwargs["approve"]
        self.approve = self.is_approved
        self.veto_reason = veto_reason
        self.penalty_score = float(penalty_score)
        self.risk_notes = risk_notes or "; ".join(kwargs.get("risk_flags", []))
        self.risk_flags = [self.risk_notes] if self.risk_notes else kwargs.get("risk_flags", [])
        self.uncertainty_score = kwargs.get("uncertainty_score", 0.0)

    def __repr__(self) -> str:
        return f"CriticVerdict(approved={self.is_approved}, veto={self.veto_reason})"


class MarketQualityScore:
    """Statistical ranking of an asset's tradability."""
    def __init__(
        self,
        trend_clarity: float = 0.0,
        volatility_health: float = 0.0,
        noise_penalty: float = 0.0,
        payout_score: float = 0.0,
        total_score: float = 0.0,
        is_tradable: bool = False,
        notes: str = "",
        **kwargs
    ):
        self.trend_clarity = trend_clarity
        self.volatility_health = volatility_health
        self.noise_penalty = noise_penalty
        self.payout_score = payout_score
        self.total_score = total_score
        self.score = self.total_score
        self.is_tradable = is_tradable
        self.notes = notes
        self.disqualification_reason = notes if not is_tradable else None

    def __repr__(self) -> str:
        return f"MarketQualityScore(total={self.total_score}, tradable={self.is_tradable}, notes={self.notes})"


class SignalGateResult:
    """Results of the 12-Gate filter evaluation."""
    def __init__(
        self,
        is_passed: bool = True,
        gates_passed: int = 12,
        total_gates: int = 12,
        failed_gate_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        self.is_passed = is_passed
        self.gates_passed = gates_passed
        self.total_gates = total_gates
        self.failed_gate_name = failed_gate_name
        self.details = details or {}
        self.value = "PASS" if is_passed else (failed_gate_name or "FAIL")

    def __repr__(self) -> str:
        return f"SignalGateResult(passed={self.is_passed} ({self.gates_passed}/{self.total_gates}), failed={self.failed_gate_name})"


class FinalSignal:
    """
    Unified Explainable Signal Model (Phase 10 & 14).
    Contains full factor evidence, lifecycle states, gate checks, and risk disclosures.
    Zero-Forced-Signal compliant.
    """
    def __init__(
        self,
        signal_id: str,
        symbol: str,
        market_type: MarketType,
        direction: Direction,
        expiration_seconds: int,
        expiration_label: str,
        entry_price: float,
        timestamp: float,
        grade: QualityGrade,
        confidence: float,
        setup_name: str,
        confluence_tags: List[str],
        critic_verdict: Optional[CriticVerdict] = None,
        gate_result: Optional[SignalGateResult] = None,
        rejection_reason: Optional[str] = None,
        timeframe: Timeframe = Timeframe.M1,
        confluence_score: Optional[float] = None,
        market_regime: Union[MarketRegime, str] = MarketRegime.UNKNOWN,
        data_quality: str = "PASS",
        trend_state: str = "NEUTRAL",
        momentum_state: str = "NEUTRAL",
        volatility_state: str = "NORMAL",
        structure_state: str = "RANGING",
        blocked_reasons: Optional[List[str]] = None,
        **kwargs
    ):
        self.signal_id = signal_id
        self.symbol = symbol
        self.asset = symbol
        self.snapshot_id = kwargs.get("snapshot_id", f"{symbol}_{int(timestamp)}")
        self.market_type = market_type
        self.timeframe = timeframe
        self.direction = direction
        self.entry_price = float(entry_price)
        self.target_exit_price = float(kwargs.get("target_exit_price", entry_price))
        self.created_at = int(timestamp)
        self.timestamp = float(timestamp)
        self.expiration_seconds = int(expiration_seconds)
        self.expiration_label = expiration_label
        self.expiration_str = expiration_label
        self.valid_until = int(timestamp + expiration_seconds)

        # Confluence & Strength (Phase 7 & 10)
        # Score is 0 - 100
        if confluence_score is not None:
            self.confluence_score = round(float(confluence_score), 1)
        else:
            self.confluence_score = round(min(100.0, max(0.0, confidence * 100.0)), 1)

        if self.confluence_score >= 85.0:
            self.signal_strength = SignalStrength.VERY_STRONG
        elif self.confluence_score >= 70.0:
            self.signal_strength = SignalStrength.STRONG
        elif self.confluence_score >= 50.0:
            self.signal_strength = SignalStrength.MODERATE
        else:
            self.signal_strength = SignalStrength.WEAK

        self.grade = grade
        self.quality_grade = grade
        self.confidence = float(confidence)
        self.confidence_percent = self.confluence_score

        # Factor states
        self.market_regime = market_regime.value if hasattr(market_regime, "value") else str(market_regime)
        self.data_quality = data_quality
        self.trend_state = trend_state
        self.momentum_state = momentum_state
        self.volatility_state = volatility_state
        self.structure_state = structure_state

        self.setup_name = setup_name
        self.primary_strategy = setup_name
        self.confluence_tags = list(confluence_tags)
        self.confirming_strategies = list(confluence_tags)
        self.reasons = list(confluence_tags)
        self.critic_verdict = critic_verdict
        self.warnings = [critic_verdict.risk_notes] if critic_verdict and critic_verdict.risk_notes else []
        self.gate_result = gate_result
        self.rejection_reason = rejection_reason
        self.blocked_reasons = blocked_reasons or ([rejection_reason] if rejection_reason else [])
        self.payout = float(kwargs.get("payout", 0.85))

        # Lifecycle State (Phase 14)
        is_valid_dir = (direction in (Direction.CALL, Direction.PUT))
        is_gate_passed = (gate_result and getattr(gate_result, "is_passed", False))
        if is_valid_dir and is_gate_passed:
            self.lifecycle_state = SignalLifecycleState.VALIDATED
            self.status = "VALID"
        else:
            self.lifecycle_state = SignalLifecycleState.INVALIDATED
            self.status = "NO_TRADE"

    def transition_to(self, new_state: SignalLifecycleState):
        """State machine transition for Signal Lifecycle (Phase 14)."""
        self.lifecycle_state = new_state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "market_type": self.market_type.value if hasattr(self.market_type, "value") else str(self.market_type),
            "timeframe": self.timeframe.value if hasattr(self.timeframe, "value") else str(self.timeframe),
            "direction": self.direction.value if hasattr(self.direction, "value") else str(self.direction),
            "entry_price": self.entry_price,
            "target_exit_price": self.target_exit_price,
            "created_at": self.created_at,
            "timestamp": self.timestamp,
            "expiration_seconds": self.expiration_seconds,
            "expiration_label": self.expiration_label,
            "signal_strength": self.signal_strength.value,
            "confluence_score": self.confluence_score,
            "market_regime": self.market_regime,
            "data_quality": self.data_quality,
            "trend_state": self.trend_state,
            "momentum_state": self.momentum_state,
            "volatility_state": self.volatility_state,
            "structure_state": self.structure_state,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "blocked_reasons": self.blocked_reasons,
            "grade": self.grade.value if hasattr(self.grade, "value") else str(self.grade),
            "status": self.status,
            "lifecycle_state": self.lifecycle_state.value,
            "rejection_reason": self.rejection_reason,
            "setup_name": self.setup_name,
            "payout": self.payout
        }

    def __repr__(self) -> str:
        return f"Signal({self.signal_id} {self.symbol} {self.direction} {self.expiration_label} Strength:{self.signal_strength.value} Score:{self.confluence_score})"


# Canonical Alias (Phase 10)
Signal = FinalSignal



@dataclass
class BacktestMetric:
    """Aggregated quantitative performance metrics."""
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sample_size: int = 0
    wins: int = 0
    losses: int = 0
    strategy_id: str = "COMPOSITE"
    status: str = "ACTIVE"
