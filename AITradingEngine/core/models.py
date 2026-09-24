"""
AITradingEngine Core Models.
Unified dataclasses representing market data, analysis snapshots, strategy votes, critic verdicts, and final signals.
Zero look-ahead bias and cross-module compatible.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

from AITradingEngine.core.enums import (
    Direction, MarketType, Timeframe, QualityGrade, MarketRegime, SignalGateResult
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
    """Complete institutional signal passed through all 12 gates."""
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
        critic_verdict: CriticVerdict,
        gate_result: SignalGateResult,
        rejection_reason: Optional[str] = None,
        **kwargs
    ):
        self.signal_id = signal_id
        self.symbol = symbol
        self.asset = symbol
        self.snapshot_id = kwargs.get("snapshot_id", f"{symbol}_{int(timestamp)}")
        self.market_type = market_type
        self.direction = direction
        self.expiration_seconds = expiration_seconds
        self.expiration_label = expiration_label
        self.expiration_str = expiration_label
        self.entry_price = entry_price
        self.target_exit_price = kwargs.get("target_exit_price", entry_price)
        self.timestamp = timestamp
        self.grade = grade
        self.quality_grade = grade
        self.confidence = confidence
        self.confidence_percent = round(confidence * 100.0, 1)
        self.setup_name = setup_name
        self.primary_strategy = setup_name
        self.confluence_tags = confluence_tags
        self.confirming_strategies = confluence_tags
        self.critic_verdict = critic_verdict
        self.gate_result = gate_result
        self.rejection_reason = rejection_reason
        self.status = "VALID" if (gate_result and gate_result.is_passed and direction != Direction.NO_SIGNAL) else "NO_TRADE"
        self.created_at = int(timestamp)
        self.valid_until = int(timestamp + expiration_seconds)
        self.reasons = confluence_tags
        self.warnings = [critic_verdict.risk_notes] if critic_verdict and critic_verdict.risk_notes else []
        self.payout = kwargs.get("payout", 0.85)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "market_type": self.market_type.value,
            "direction": self.direction.value,
            "expiration_label": self.expiration_label,
            "expiration_seconds": self.expiration_seconds,
            "entry_price": self.entry_price,
            "timestamp": self.timestamp,
            "grade": self.grade.value,
            "confidence": self.confidence,
            "setup_name": self.setup_name,
            "confluence_tags": self.confluence_tags,
            "status": self.status,
            "rejection_reason": self.rejection_reason
        }

    def __repr__(self) -> str:
        return f"FinalSignal({self.signal_id} {self.symbol} {self.direction.value} {self.expiration_label} Grade:{self.grade.value})"


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
