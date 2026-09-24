"""
AITradingEngine Core Enums.
Defines all domain constants, states, market types, timeframes, lifecycle states, and rejection reasons.
"""
from enum import Enum


class Direction(str, Enum):
    CALL = "CALL"
    PUT = "PUT"
    NO_SIGNAL = "NO_SIGNAL"


class MarketType(str, Enum):
    OTC = "OTC"
    REAL = "REAL"


class Timeframe(str, Enum):
    # Short style
    S5 = "5s"
    S15 = "15s"
    S30 = "30s"
    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"

    # Prefixed style
    TF_5S = "5s"
    TF_15S = "15s"
    TF_30S = "30s"
    TF_1M = "1m"
    TF_3M = "3m"
    TF_5M = "5m"
    TF_15M = "15m"


class QualityGrade(str, Enum):
    GRADE_A = "GRADE_A"       # High confluence, large historical sample, high expectancy
    GRADE_B = "GRADE_B"       # Standard confluence, acceptable edge
    NO_TRADE = "NO_TRADE"     # Inconclusive, noisy, conflicting, or low edge


class SignalStrength(str, Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


class SignalLifecycleState(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SENT = "SENT"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    WIN = "WIN"
    LOSS = "LOSS"
    CANCELLED = "CANCELLED"
    INVALIDATED = "INVALIDATED"


class MarketRegime(str, Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    BREAKOUT = "BREAKOUT"
    REVERSAL = "REVERSAL"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    CHOPPY = "CHOPPY"
    UNSTABLE = "UNSTABLE"
    UNKNOWN = "UNKNOWN"


class SystemState(str, Enum):
    SCANNING = "SCANNING"
    ANALYZING = "ANALYZING"
    VALIDATING = "VALIDATING"
    SIGNAL_READY = "SIGNAL_READY"
    SIGNAL_SENT = "SIGNAL_SENT"
    SIGNAL_INVALIDATED = "SIGNAL_INVALIDATED"
    NO_TRADE = "NO_TRADE"
    MARKET_UNSTABLE = "MARKET_UNSTABLE"
    DATA_ERROR = "DATA_ERROR"
    STRATEGY_SUSPENDED = "STRATEGY_SUSPENDED"
    SYSTEM_PAUSED = "SYSTEM_PAUSED"


class StrategyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    UNDER_REVIEW = "UNDER_REVIEW"
    SUSPENDED = "SUSPENDED"


class SignalGateResult(str, Enum):
    PASS = "PASS"
    REJECT_DATA_QUALITY = "REJECT_DATA_QUALITY"
    REJECT_MARKET_CHOP = "REJECT_MARKET_CHOP"
    REJECT_MTF_CONFLICT = "REJECT_MTF_CONFLICT"
    REJECT_LOW_CONFLUENCE = "REJECT_LOW_CONFLUENCE"
    REJECT_STRATEGY_CONFLICT = "REJECT_STRATEGY_CONFLICT"
    REJECT_NO_STATISTICAL_EDGE = "REJECT_NO_STATISTICAL_EDGE"
    REJECT_STRATEGY_SUSPENDED = "REJECT_STRATEGY_SUSPENDED"
    REJECT_MARKET_NOISE = "REJECT_MARKET_NOISE"
    REJECT_LOW_PAYOUT = "REJECT_LOW_PAYOUT"
    REJECT_COOLDOWN_ACTIVE = "REJECT_COOLDOWN_ACTIVE"
    REJECT_DRAWDOWN_SHIELD = "REJECT_DRAWDOWN_SHIELD"
    REJECT_PRE_EXECUTION_DRIFT = "REJECT_PRE_EXECUTION_DRIFT"
    REJECT_CRITIC_VETO = "REJECT_CRITIC_VETO"
    REJECT_HIGH_UNCERTAINTY = "REJECT_HIGH_UNCERTAINTY"
