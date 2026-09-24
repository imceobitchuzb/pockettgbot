"""
12-Gate Signal Pipeline & Quality Filter.
Implements the institutional 12-layer verification pipeline.
Every single candidate trade must pass all 12 gates sequentially.
Any single failure immediately aborts trade generation and logs rejection (Zero-Forced-Signal).
"""
import uuid
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from AITradingEngine.core.enums import Direction, MarketRegime, QualityGrade
from AITradingEngine.core.models import (
    MarketSnapshot,
    StrategyVote,
    CriticVerdict,
    SignalGateResult,
    FinalSignal
)
from AITradingEngine.signal_engine.expiration_optimizer import ExpirationOptimizer
from AITradingEngine.signal_engine.pre_signal_recheck import PreSignalRecheck
from AITradingEngine.database.repository import EngineRepository

logger = logging.getLogger("AITradingEngine.SignalGate")


class SignalGatePipeline:
    """Evaluates candidate setups through 12 independent institutional filters."""

    def __init__(self, repository: Optional[EngineRepository] = None):
        self.repository = repository
        self.expiration_optimizer = ExpirationOptimizer()
        self.pre_signal_recheck = PreSignalRecheck()

    def evaluate_pipeline(
        self,
        snapshot: MarketSnapshot,
        dominant_direction: Direction,
        setup_name: str,
        confluence_tags: List[str],
        strategy_votes: List[StrategyVote],
        critic_verdict: CriticVerdict,
        calibrated_prob: float,
        expected_value: float,
        latency_ms: float = 45.0,
        latest_tick_price: Optional[float] = None,
        is_strategy_suspended: bool = False,
        is_risk_cooldown_active: bool = False
    ) -> FinalSignal:
        """
        Runs candidate through all 12 gates.
        Returns FinalSignal (with Direction.NO_SIGNAL and QualityGrade.NO_TRADE if failed).
        """
        signal_id = f"#{uuid.uuid4().hex[:6].upper()}"
        now_ts = time.time()
        payout = snapshot.payout
        ind = snapshot.indicators
        atr = ind.get("atr", 0.0005)
        tick_price = latest_tick_price if latest_tick_price is not None else snapshot.current_price

        # Track gate progress
        passed_count = 0
        gate_details = {}

        def reject(gate_num: int, gate_name: str, reason: str) -> FinalSignal:
            logger.info(f"[REJECTION] Signal {signal_id} rejected at Gate {gate_num} ({gate_name}): {reason}")
            gate_res = SignalGateResult(
                is_passed=False,
                gates_passed=passed_count,
                total_gates=12,
                failed_gate_name=gate_name,
                details=gate_details
            )
            # Log rejection to database
            if self.repository:
                try:
                    self.repository.save_rejection(
                        symbol=snapshot.symbol,
                        gate_name=gate_name,
                        reason=reason,
                        snapshot_data={"price": snapshot.current_price, "regime": snapshot.regime.value}
                    )
                except Exception as e:
                    logger.error(f"Failed to log rejection to DB: {e}")

            return FinalSignal(
                signal_id=signal_id,
                symbol=snapshot.symbol,
                market_type=snapshot.market_type,
                direction=Direction.NO_SIGNAL,
                expiration_seconds=0,
                expiration_label="N/A",
                entry_price=snapshot.current_price,
                timestamp=now_ts,
                grade=QualityGrade.NO_TRADE,
                confidence=calibrated_prob,
                setup_name=setup_name,
                confluence_tags=confluence_tags,
                critic_verdict=critic_verdict,
                gate_result=gate_res,
                rejection_reason=f"Gate {gate_num} ({gate_name}): {reason}"
            )

        # -------------------------------------------------------------
        # Gate 1: Market Data Quality & Latency
        # -------------------------------------------------------------
        if latency_ms > 350.0:
            return reject(1, "DataLatency", f"Latency too high ({latency_ms:.1f}ms > 350ms)")
        if not snapshot.candles or len(snapshot.candles) < 20:
            return reject(1, "DataHealth", "Insufficient candle depth for analysis")
        passed_count += 1
        gate_details["gate_1_data"] = "PASS"

        # -------------------------------------------------------------
        # Gate 2: Market Regime Tradability
        # -------------------------------------------------------------
        if snapshot.regime in (MarketRegime.CHOPPY, MarketRegime.UNSTABLE):
            return reject(2, "RegimeFilter", f"Untradable market regime: {snapshot.regime.value}")
        passed_count += 1
        gate_details["gate_2_regime"] = "PASS"

        # -------------------------------------------------------------
        # Gate 3: MTF Concordance
        # -------------------------------------------------------------
        if snapshot.mtf_alignment and snapshot.mtf_alignment.has_conflict:
            return reject(3, "MTFConcordance", "Multi-Timeframe directional conflict detected")
        passed_count += 1
        gate_details["gate_3_mtf"] = "PASS"

        # -------------------------------------------------------------
        # Gate 4: Minimum Confluence Threshold (>= 3 independent factors)
        # -------------------------------------------------------------
        if len(confluence_tags) < 3:
            return reject(4, "ConfluenceThreshold", f"Insufficient confluence ({len(confluence_tags)} < 3)")
        passed_count += 1
        gate_details["gate_4_confluence"] = "PASS"

        # -------------------------------------------------------------
        # Gate 5: Strategy Consensus (Zero Conflict)
        # -------------------------------------------------------------
        call_votes = [v for v in strategy_votes if v.direction == Direction.CALL and v.confidence >= 0.65]
        put_votes = [v for v in strategy_votes if v.direction == Direction.PUT and v.confidence >= 0.65]
        if call_votes and put_votes:
            return reject(5, "StrategyConsensus", "Disagreement between active strategy votes")
        passed_count += 1
        gate_details["gate_5_consensus"] = "PASS"

        # -------------------------------------------------------------
        # Gate 6: Historical Statistical Edge (EV >= +0.05)
        # -------------------------------------------------------------
        if expected_value < 0.05:
            return reject(6, "StatisticalEdge", f"Insufficient mathematical edge (EV={expected_value:.3f} < +0.05)")
        passed_count += 1
        gate_details["gate_6_edge"] = "PASS"

        # -------------------------------------------------------------
        # Gate 7: Walk-Forward Out-Of-Sample Confirmation
        # -------------------------------------------------------------
        if is_strategy_suspended:
            return reject(7, "WalkForwardStatus", f"Strategy {setup_name} is currently suspended due to concept drift")
        passed_count += 1
        gate_details["gate_7_walk_forward"] = "PASS"

        # -------------------------------------------------------------
        # Gate 8: Volatility Health
        # -------------------------------------------------------------
        avg_price = snapshot.current_price
        atr_pct = (atr / avg_price) * 100.0 if avg_price > 0 else 0.0
        if atr_pct < 0.01:
            return reject(8, "VolatilityHealth", f"Dead market - ATR too low ({atr_pct:.4f}%)")
        if atr_pct > 0.50:
            return reject(8, "VolatilityHealth", f"Abnormal volatility spike ({atr_pct:.4f}%)")
        passed_count += 1
        gate_details["gate_8_volatility"] = "PASS"

        # -------------------------------------------------------------
        # Gate 9: Noise & Choppiness Index
        # -------------------------------------------------------------
        ci = ind.get("choppiness_index", 50.0)
        if ci > 61.8:
            return reject(9, "NoiseChoppiness", f"Market Choppiness Index too high ({ci:.1f} > 61.8)")
        passed_count += 1
        gate_details["gate_9_noise"] = "PASS"

        # -------------------------------------------------------------
        # Gate 10: Broker Payout Threshold (Payout >= 0.80)
        # -------------------------------------------------------------
        if payout < 0.80:
            return reject(10, "PayoutThreshold", f"Broker payout insufficient ({int(payout * 100)}% < 80%)")
        passed_count += 1
        gate_details["gate_10_payout"] = "PASS"

        # -------------------------------------------------------------
        # Gate 11: Risk Management & Cooldown Check
        # -------------------------------------------------------------
        if is_risk_cooldown_active:
            return reject(11, "RiskManagement", "Risk engine cooldown active for this asset / account")
        passed_count += 1
        gate_details["gate_11_risk"] = "PASS"

        # -------------------------------------------------------------
        # Gate 12: Pre-Signal Micro Recheck
        # -------------------------------------------------------------
        is_recheck_ok, recheck_msg = self.pre_signal_recheck.recheck(
            direction=dominant_direction,
            snapshot_price=snapshot.current_price,
            latest_tick_price=tick_price,
            atr=atr,
            current_latency_ms=latency_ms
        )
        if not is_recheck_ok:
            return reject(12, "PreSignalRecheck", recheck_msg)
        passed_count += 1
        gate_details["gate_12_recheck"] = "PASS"

        # -------------------------------------------------------------
        # ALL 12 GATES PASSED! Build Institutional Signal
        # -------------------------------------------------------------
        opt_exp = self.expiration_optimizer.optimize_expiration(
            timeframe=snapshot.primary_timeframe,
            setup_name=setup_name,
            regime=snapshot.regime,
            atr=atr
        )

        grade = QualityGrade.GRADE_A if (calibrated_prob >= 0.80 and len(confluence_tags) >= 4) else QualityGrade.GRADE_B

        final_sig = FinalSignal(
            signal_id=signal_id,
            symbol=snapshot.symbol,
            market_type=snapshot.market_type,
            direction=dominant_direction,
            expiration_seconds=opt_exp["expiration_sec"],
            expiration_label=opt_exp["expiration_label"],
            entry_price=tick_price,
            timestamp=now_ts,
            grade=grade,
            confidence=calibrated_prob,
            setup_name=setup_name,
            confluence_tags=confluence_tags,
            critic_verdict=critic_verdict,
            gate_result=SignalGateResult(
                is_passed=True,
                gates_passed=12,
                total_gates=12,
                failed_gate_name=None,
                details=gate_details
            ),
            rejection_reason=None
        )

        if self.repository:
            try:
                self.repository.save_signal(final_sig)
            except Exception as e:
                logger.error(f"Failed to record signal in DB: {e}")

        logger.info(
            f"[SIGNAL APPROVED] {final_sig.signal_id} on {final_sig.symbol} "
            f"({final_sig.direction.value}) {final_sig.expiration_label} | Grade: {final_sig.grade.value} | Conf: {int(final_sig.confidence * 100)}%"
        )
        return final_sig
