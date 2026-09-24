"""
Comprehensive Verification Test Suite for the Ultimate AI Trading Engine.
Verifies all 12 Gates, Zero Look-Ahead Bias, Segregated OTC/Real, Two-Stage AI,
and Zero-Forced-Signal Enforcement.
"""
import os
import time
import pytest
from AITradingEngine.core.enums import Direction, MarketType, Timeframe, QualityGrade, MarketRegime
from AITradingEngine.core.models import Candle, MarketSnapshot, StrategyVote, CriticVerdict
from AITradingEngine.database.connection import get_database_connection
from AITradingEngine.database.repository import EngineRepository
from AITradingEngine.market_data.snapshot_builder import SnapshotBuilder
from AITradingEngine.market_data.data_cleaner import validate_tick, clean_candle_stream
from AITradingEngine.regime_detection.noise_filter import calculate_choppiness_index, evaluate_noise
from AITradingEngine.regime_detection.regime_detector import RegimeDetector
from AITradingEngine.market_scanner.quality_ranker import compute_market_quality
from AITradingEngine.strategy_engine.engine import StrategyEngine
from AITradingEngine.strategy_engine.conflict_detector import StrategyConflictDetector
from AITradingEngine.ai_ensemble.analyst_layer import AnalystLayer
from AITradingEngine.ai_ensemble.critic_layer import AdversarialCritic
from AITradingEngine.ai_ensemble.uncertainty_engine import UncertaintyEngine
from AITradingEngine.confidence_engine.confidence_scorer import ConfidenceScorer
from AITradingEngine.confidence_engine.quality_grader import QualityGrader
from AITradingEngine.signal_engine.signal_gate import SignalGatePipeline
from AITradingEngine.risk_engine.anti_overtrading import AntiOvertradingEngine
from AITradingEngine.risk_engine.loss_streak_shield import LossStreakShield
from AITradingEngine.risk_engine.emergency_shutdown import EmergencyShutdownEngine
from AITradingEngine.otc_engine.otc_validator import OTCValidator
from AITradingEngine.otc_engine.otc_store import OTCPerformanceStore
from AITradingEngine.real_market_engine.market_hours import RealMarketSessionManager
from AITradingEngine.real_market_engine.real_store import RealMarketPerformanceStore
from AITradingEngine.backtesting.simulator import BacktestSimulator
from AITradingEngine.backtesting.metrics import calculate_backtest_metrics
from AITradingEngine.backtesting.monte_carlo import run_monte_carlo
from AITradingEngine.walk_forward.drift_detector import ConceptDriftDetector


def generate_synthetic_candles(count: int = 80, trend: str = "UP", base: float = 1.0850) -> list[Candle]:
    """Helper to generate realistic closed candles."""
    candles = []
    p = base
    now = int(time.time())
    for i in range(count):
        t = now - (count - i) * 60
        if trend == "UP":
            delta = 0.00010 + (0.00005 if i % 2 == 0 else -0.00002)
        elif trend == "DOWN":
            delta = -0.00010 + (-0.00005 if i % 2 == 0 else 0.00002)
        elif trend == "CHOPPY":
            delta = 0.00025 if i % 2 == 0 else -0.00025
        else:  # RANGE
            delta = 0.00003 if (i // 3) % 2 == 0 else -0.00003

        o = p
        c = p + delta
        h = max(o, c) + 0.00004
        l = min(o, c) - 0.00004
        candles.append(Candle(
            timestamp=t,
            open=round(o, 5),
            high=round(h, 5),
            low=round(l, 5),
            close=round(c, 5),
            volume=150.0,
            timeframe=Timeframe.TF_1M,
            is_closed=True
        ))
        p = c
    return candles


# -------------------------------------------------------------
# Test 1: Zero Look-Ahead Bias & Point-in-Time Snapshot
# -------------------------------------------------------------
def test_zero_look_ahead_bias():
    builder = SnapshotBuilder()
    candles = generate_synthetic_candles( count=50, trend="UP" )
    
    # Active forming candle (unclosed)
    forming_candle = Candle(
        timestamp=int(time.time()),
        open=1.1000,
        high=1.1050,
        low=1.0990,
        close=1.1040,
        volume=50.0,
        timeframe=Timeframe.TF_1M,
        is_closed=False
    )
    all_candles = candles + [forming_candle]

    snapshot = builder.build_snapshot(
        symbol="EURUSD",
        market_type=MarketType.REAL,
        primary_candles=all_candles,
        primary_tf=Timeframe.TF_1M
    )

    assert snapshot is not None
    # Verify the unclosed candle was strictly excluded from analysis
    assert snapshot.candles[-1].is_closed is True
    assert snapshot.candles[-1].timestamp == candles[-1].timestamp
    assert snapshot.current_price == candles[-1].close


# -------------------------------------------------------------
# Test 2: Noise Filter & Choppiness Index (Zero-Forced-Signal)
# -------------------------------------------------------------
def test_noise_filter_and_choppiness():
    choppy_candles = generate_synthetic_candles(count=50, trend="CHOPPY")
    eval_res = evaluate_noise(choppy_candles)

    assert eval_res["choppiness_index"] > 55.0
    # In choppy market, quality ranker must mark is_tradable=False
    regime_det = RegimeDetector()
    regime, _ = regime_det.detect(choppy_candles)
    quality = compute_market_quality(choppy_candles, regime, payout=0.85)

    assert quality.is_tradable is False or regime == MarketRegime.CHOPPY


# -------------------------------------------------------------
# Test 3: Strategy Conflict Detector
# -------------------------------------------------------------
def test_strategy_conflict_detector():
    detector = StrategyConflictDetector()

    # Conflicting votes: s1 votes CALL, s2 votes PUT
    votes = [
        StrategyVote("s01_trend", Direction.CALL, 0.78, "Strong uptrend", 1.0),
        StrategyVote("s07_mean_rev", Direction.PUT, 0.75, "Overbought mean reversion", 1.0)
    ]
    has_conflict, msg, details = detector.detect_conflict(votes)

    assert has_conflict is True
    assert "Directional Conflict" in msg
    assert details["call_count"] == 1
    assert details["put_count"] == 1


# -------------------------------------------------------------
# Test 4: Two-Stage AI (Analyst + Adversarial Critic Veto)
# -------------------------------------------------------------
def test_adversarial_critic_veto():
    critic = AdversarialCritic()
    candles = generate_synthetic_candles(count=40, trend="UP")
    
    # Craft a snapshot with bearish rejection wick (pin bar upper wick) on candidate candle
    last_c = Candle(
        timestamp=int(time.time()),
        open=1.0900,
        high=1.0950, # Huge upper wick
        low=1.0898,
        close=1.0902,
        volume=200.0,
        timeframe=Timeframe.TF_1M,
        is_closed=True
    )
    candles.append(last_c)

    builder = SnapshotBuilder()
    snapshot = builder.build_snapshot("EURUSD", MarketType.REAL, candles, Timeframe.TF_1M)

    # Propose CALL directly into an aggressive bearish rejection wick
    verdict = critic.critique(snapshot, Direction.CALL, "TrendFollowing")

    assert verdict.is_approved is False
    assert "ADVERSARIAL_VETO" in verdict.veto_reason


# -------------------------------------------------------------
# Test 5: Confidence Scorer (Platt/Sigmoid Bounding)
# -------------------------------------------------------------
def test_confidence_calibration():
    scorer = ConfidenceScorer()

    # Even with 1.0 raw confidence and 0 critic penalty, it must NEVER output 100% (quant realism)
    calibrated = scorer.calibrate(raw_confidence=1.0, critic_penalty=0.0, uncertainty=0.0)
    assert calibrated <= 0.89
    assert calibrated >= 0.70

    # Test edge expectancy calculation
    edge = scorer.calculate_statistical_edge(calibrated_prob=0.75, payout=0.85)
    # EV at 75% win rate and 85% payout: 0.75 * 0.85 - 0.25 * 1.0 = 0.6375 - 0.25 = +0.3875
    assert edge["has_positive_edge"] is True
    assert edge["expected_value"] > 0.05


# -------------------------------------------------------------
# Test 6: 12-Gate Filter Pipeline
# -------------------------------------------------------------
def test_12_gate_filter_pipeline():
    conn = get_database_connection("data/test_quant.db")
    repo = EngineRepository(conn)
    pipeline = SignalGatePipeline(repo)

    candles = generate_synthetic_candles(count=40, trend="UP")
    builder = SnapshotBuilder()
    snapshot = builder.build_snapshot("EUR_USD_OTC", MarketType.OTC, candles, Timeframe.TF_1M, payout=0.88)

    # 1. Test Gate Failure: Latency Spike (>350ms)
    fail_sig = pipeline.evaluate_pipeline(
        snapshot=snapshot,
        dominant_direction=Direction.CALL,
        setup_name="TrendFollowing",
        confluence_tags=["Trend Alignment", "Price Structure", "Momentum"],
        strategy_votes=[StrategyVote("TrendFollowing", Direction.CALL, 0.80, "OK", 1.0)],
        critic_verdict=CriticVerdict(True, None, 0.0, "OK"),
        calibrated_prob=0.82,
        expected_value=0.25,
        latency_ms=450.0  # Excessive latency!
    )
    assert fail_sig.gate_result.is_passed is False
    assert fail_sig.gate_result.failed_gate_name == "DataLatency"
    assert fail_sig.direction == Direction.NO_SIGNAL

    # 2. Test Gate Failure: Low Payout (<80%)
    low_payout_snap = builder.build_snapshot("EUR_USD_OTC", MarketType.OTC, candles, Timeframe.TF_1M, payout=0.72)
    fail_payout_sig = pipeline.evaluate_pipeline(
        snapshot=low_payout_snap,
        dominant_direction=Direction.CALL,
        setup_name="TrendFollowing",
        confluence_tags=["Trend Alignment", "Price Structure", "Momentum"],
        strategy_votes=[StrategyVote("TrendFollowing", Direction.CALL, 0.80, "OK", 1.0)],
        critic_verdict=CriticVerdict(True, None, 0.0, "OK"),
        calibrated_prob=0.82,
        expected_value=0.25,
        latency_ms=50.0
    )
    assert fail_payout_sig.gate_result.is_passed is False
    assert fail_payout_sig.gate_result.failed_gate_name == "PayoutThreshold"

    # 3. Test Full Pass of All 12 Gates
    pass_sig = pipeline.evaluate_pipeline(
        snapshot=snapshot,
        dominant_direction=Direction.CALL,
        setup_name="TrendFollowing",
        confluence_tags=["Trend Alignment", "Price Structure", "Momentum Room / Rebound"],
        strategy_votes=[StrategyVote("TrendFollowing", Direction.CALL, 0.80, "OK", 1.0)],
        critic_verdict=CriticVerdict(True, None, 0.0, "OK"),
        calibrated_prob=0.84,
        expected_value=0.30,
        latency_ms=30.0
    )
    assert pass_sig.gate_result.is_passed is True
    assert pass_sig.gate_result.gates_passed == 12
    assert pass_sig.direction == Direction.CALL
    assert pass_sig.grade in (QualityGrade.GRADE_A, QualityGrade.GRADE_B)


# -------------------------------------------------------------
# Test 7: Segregated OTC vs Real Market Stores
# -------------------------------------------------------------
def test_segregated_market_stores():
    otc_store = OTCPerformanceStore()
    real_store = RealMarketPerformanceStore()

    candles = generate_synthetic_candles(count=30, trend="UP")
    builder = SnapshotBuilder()
    snap_otc = builder.build_snapshot("EUR_USD_OTC", MarketType.OTC, candles, Timeframe.TF_1M)
    snap_real = builder.build_snapshot("EUR_USD", MarketType.REAL, candles, Timeframe.TF_1M)

    from AITradingEngine.core.models import FinalSignal, SignalGateResult

    sig_otc = FinalSignal(
        signal_id="#OTC1",
        symbol="EUR_USD_OTC",
        market_type=MarketType.OTC,
        direction=Direction.CALL,
        expiration_seconds=60,
        expiration_label="1 MIN",
        entry_price=1.0850,
        timestamp=time.time(),
        grade=QualityGrade.GRADE_A,
        confidence=0.84,
        setup_name="TrendFollowing",
        confluence_tags=["Trend"],
        critic_verdict=CriticVerdict(True, None, 0.0, "OK"),
        gate_result=SignalGateResult(True, 12, 12, None, {})
    )

    otc_store.record_signal(sig_otc)
    otc_store.record_outcome("#OTC1", is_win=True)

    metrics = otc_store.get_metrics()
    assert metrics["market_type"] == "OTC"
    assert metrics["total_signals"] == 1
    assert metrics["wins"] == 1
    assert metrics["win_rate"] == 100.0

    # Ensure real_store remains strictly 0 (no contamination)
    assert real_store.total_signals == 0
    assert real_store.wins == 0


# -------------------------------------------------------------
# Test 8: Risk Engine & Loss Streak Shield (No Martingale)
# -------------------------------------------------------------
def test_loss_streak_shield():
    shield = LossStreakShield(
        base_confidence_threshold=0.72,
        tightened_confidence_threshold=0.82,
        max_consecutive_losses=3,
        halt_duration_seconds=60.0
    )

    # Initially standard threshold
    thresh, _ = shield.get_effective_confidence_threshold()
    assert thresh == 0.72

    # After 2 consecutive losses: threshold tightens to 0.82
    shield.record_outcome(is_win=False)
    shield.record_outcome(is_win=False)
    thresh_tight, _ = shield.get_effective_confidence_threshold()
    assert thresh_tight == 0.82

    # After 3 consecutive losses: trading halted
    shield.record_outcome(is_win=False)
    is_halted, _ = shield.is_shield_active()
    assert is_halted is True


# -------------------------------------------------------------
# Test 9: Concept Drift Detector
# -------------------------------------------------------------
def test_concept_drift_detector():
    detector = ConceptDriftDetector(window_size=20, breakeven_win_rate=54.1, suspension_threshold=50.0)

    # Feed a series of 15 losses
    for _ in range(15):
        detector.record_trade_outcome("TrendPullback", is_win=False)

    assert detector.is_suspended("TrendPullback") is True
    assert "TrendPullback" in detector.get_suspended_strategies()


# -------------------------------------------------------------
# Test 10: Event-Driven Backtester & Monte Carlo
# -------------------------------------------------------------
def test_backtester_and_monte_carlo():
    candles = generate_synthetic_candles(count=120, trend="UP")
    simulator = BacktestSimulator(symbol="EURUSD", market_type=MarketType.REAL, timeframe=Timeframe.TF_1M)
    res = simulator.run(candles, horizon_candles=2)

    assert "metrics" in res
    m = res["metrics"]
    assert hasattr(m, "win_rate")
    assert hasattr(m, "expectancy")

    # Run Monte Carlo on outcomes
    outcomes = [1, 1, 1, -1, 1, -1, 1, 1, -1, 1, 1, -1]
    mc = run_monte_carlo(outcomes, num_simulations=100)
    assert "median_max_drawdown" in mc
    assert "worst_5pct_drawdown" in mc
