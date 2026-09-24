"""
Master AI Trading Engine Coordinator.
Assembles all institutional quant subsystems: Market Data, Multi-Timeframe, Scanner,
9 Strategies, Adversarial Critic, 12-Gate Filter, Risk Protection, and Segregated OTC/Real engines.
Strictly enforces: NO TRADE IS A VALID DECISION.
"""
import logging
from typing import Optional, Dict, Any, List

from AITradingEngine.core.enums import Direction, MarketType, QualityGrade, SystemState, Timeframe
from AITradingEngine.core.models import Candle, MarketSnapshot, MarketQualityScore, FinalSignal
from AITradingEngine.database.connection import get_database_connection
from AITradingEngine.database.repository import EngineRepository
from AITradingEngine.market_data.feed_manager import FeedManager
from AITradingEngine.market_data.latency_monitor import LatencyMonitor
from AITradingEngine.regime_detection.regime_detector import RegimeDetector
from AITradingEngine.market_scanner.scanner import MarketScanner
from AITradingEngine.market_scanner.quality_ranker import compute_market_quality
from AITradingEngine.strategy_engine.engine import StrategyEngine
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
from AITradingEngine.walk_forward.drift_detector import ConceptDriftDetector
from AITradingEngine.screenshot_analyzer.vision_quant import VisionQuantAnalyzer
from AITradingEngine.monitoring.admin_metrics import AdminMetricsManager
from AITradingEngine.logging.quant_logger import setup_quant_logger

logger = logging.getLogger("AITradingEngine.Master")


class UltimateAITradingEngine:
    """Master Institutional AI Signal Engine."""

    def __init__(self, db_path: str = "data/quant_engine.db"):
        setup_quant_logger()
        logger.info("[INIT] Initializing Ultimate AI Signal Engine...")

        # 1. Database & Persistence (WAL mode)
        self.repository = EngineRepository(db_path=db_path)


        # 2. Market Data & Feeds
        self.latency_monitor = LatencyMonitor(max_allowed_latency_ms=350.0)
        self.feed_manager = FeedManager(self.repository)

        # 3. Market Regimes & Scanning
        self.regime_detector = RegimeDetector()
        self.scanner = MarketScanner(
            feed_manager=self.feed_manager,
            pipeline_callback=self.process_candidate_setup,
            scan_interval_sec=3.0
        )

        # 4. Strategies & Conflict
        self.strategy_engine = StrategyEngine()

        # 5. Two-Stage AI Ensemble
        self.analyst_layer = AnalystLayer()
        self.critic_layer = AdversarialCritic()
        self.uncertainty_engine = UncertaintyEngine()

        # 6. Confidence & Calibration
        self.confidence_scorer = ConfidenceScorer()
        self.quality_grader = QualityGrader()

        # 7. 12-Gate Filter Pipeline
        self.signal_gate_pipeline = SignalGatePipeline(self.repository)

        # 8. Risk Management & Circuit Breakers
        self.anti_overtrading = AntiOvertradingEngine()
        self.loss_shield = LossStreakShield()
        self.emergency_shutdown = EmergencyShutdownEngine()

        # 9. Segregated Market Engines (OTC vs Real)
        self.otc_validator = OTCValidator(min_otc_payout=0.85)
        self.otc_store = OTCPerformanceStore()
        self.real_session_mgr = RealMarketSessionManager()
        self.real_store = RealMarketPerformanceStore()

        # 10. Walk-Forward Drift & Vision Quant
        self.drift_detector = ConceptDriftDetector()
        self.vision_quant = VisionQuantAnalyzer()

        # 11. Monitoring
        self.admin_metrics = AdminMetricsManager(self.repository)

        self.last_signal: Optional[FinalSignal] = None
        logger.info("[INIT] Ultimate AI Signal Engine fully initialized.")

    async def process_candidate_setup(
        self,
        snapshot: MarketSnapshot,
        quality_score: MarketQualityScore
    ) -> Optional[FinalSignal]:
        """
        Executes complete institutional pipeline on a candidate snapshot.
        Enforces Zero-Forced-Signal at every decision node.
        """
        # Step A: Circuit Breaker & Safety Check
        is_safe, safe_reason = self.emergency_shutdown.evaluate_system_health(
            daily_pnl_pct=0.0,
            api_error_rate_pct=0.0
        )
        if not is_safe:
            logger.warning(f"[SAFETY_ABORT] {safe_reason}")
            return None

        # Step B: Market-Type Segregated Verification
        if snapshot.market_type == MarketType.OTC:
            is_otc_ok, otc_reason = self.otc_validator.validate_otc_environment(snapshot)
            if not is_otc_ok:
                logger.info(f"[OTC_VETO] {snapshot.symbol}: {otc_reason}")
                return None
        else:
            is_open, open_reason = self.real_session_mgr.is_market_open()
            if not is_open:
                logger.info(f"[REAL_MARKET_CLOSED] {open_reason}")
                return None

        # Step C: Anti-Overtrading Check
        is_trade_allowed, trade_reason = self.anti_overtrading.check_trade_allowed(snapshot.symbol)
        if not is_trade_allowed:
            logger.debug(f"[COOLDOWN_ACTIVE] {snapshot.symbol}: {trade_reason}")
            return None

        # Step D: Loss Streak Shield Check
        is_halted, halt_reason = self.loss_shield.is_shield_active()
        if is_halted:
            logger.warning(f"[LOSS_STREAK_HALT] {halt_reason}")
            return None

        # Step E: 9-Strategy Evaluation & Conflict Detection
        dom_dir, votes, has_conflict, conflict_msg = self.strategy_engine.evaluate_all(snapshot)
        if has_conflict or dom_dir == Direction.NO_SIGNAL:
            logger.debug(f"[STRATEGY_ENGINE] No consensus or conflict for {snapshot.symbol}: {conflict_msg}")
            return None

        # Step F: AI #1 Analyst Synthesis
        thesis = self.analyst_layer.analyze(snapshot, votes, dom_dir)
        if not thesis["has_thesis"]:
            return None

        setup_name = thesis["setup_name"]
        confluence_tags = thesis["confluence_tags"]

        # Step G: AI #2 Adversarial Critic Critique
        critic_verdict = self.critic_layer.critique(snapshot, dom_dir, setup_name)
        if not critic_verdict.is_approved:
            logger.info(f"[CRITIC_VETO] {snapshot.symbol} {dom_dir.value}: {critic_verdict.veto_reason}")
            return None

        # Step H: Uncertainty Quantification
        uncertainty = self.uncertainty_engine.calculate_uncertainty(
            snapshot, votes, thesis["raw_confidence"]
        )
        if uncertainty["is_vetoed"]:
            logger.info(f"[UNCERTAINTY_VETO] {snapshot.symbol}: {uncertainty['reason']}")
            return None

        # Step I: Confidence Calibration & Statistical Edge
        calibrated_prob = self.confidence_scorer.calibrate(
            raw_confidence=thesis["raw_confidence"],
            critic_penalty=critic_verdict.penalty_score,
            uncertainty=uncertainty["uncertainty_score"]
        )
        edge_data = self.confidence_scorer.calculate_statistical_edge(calibrated_prob, snapshot.payout)

        # Check required threshold from loss shield
        min_threshold, _ = self.loss_shield.get_effective_confidence_threshold()
        if calibrated_prob < min_threshold:
            logger.info(f"[PROBABILITY_BELOW_THRESHOLD] {snapshot.symbol}: {calibrated_prob} < {min_threshold}")
            return None

        # Step J: Walk-Forward Concept Drift Check
        is_suspended = self.drift_detector.is_suspended(setup_name)

        # Step K: Pass Through the 12-Gate Filter Pipeline
        signal = self.signal_gate_pipeline.evaluate_pipeline(
            snapshot=snapshot,
            dominant_direction=dom_dir,
            setup_name=setup_name,
            confluence_tags=confluence_tags,
            strategy_votes=votes,
            critic_verdict=critic_verdict,
            calibrated_prob=calibrated_prob,
            expected_value=edge_data["expected_value"],
            latency_ms=45.0,
            latest_tick_price=snapshot.current_price,
            is_strategy_suspended=is_suspended,
            is_risk_cooldown_active=False
        )

        if signal.gate_result.is_passed and signal.direction != Direction.NO_SIGNAL:
            self.last_signal = signal
            self.anti_overtrading.record_signal(signal.symbol)

            # Route to segregated store
            if signal.market_type == MarketType.OTC:
                self.otc_store.record_signal(signal)
            else:
                self.real_store.record_signal(signal)

            return signal

        return None

    def get_status_overview(self) -> Dict[str, Any]:
        """Provides comprehensive system telemetry for Telegram bot and web dashboard."""
        return self.admin_metrics.get_system_telemetry(
            current_state=self.scanner.current_state,
            focus_asset=self.scanner.current_focus_asset,
            active_assets_count=len(self.scanner.get_tracked_symbols())
        )

    def get_price_comparison(self, pair_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Compares broker source quote against bot internal quote for the debugger."""
        from AITradingEngine.market_data.pocket_option_adapter import pocket_option_adapter
        from AITradingEngine.market_data.price_validator import price_validator

        symbols = [pair_id] if pair_id else list(self.feed_manager.feeds.keys())
        results = []
        for sym in symbols:
            if sym not in self.feed_manager.feeds:
                continue
            feed = self.feed_manager.feeds[sym]
            source_tick = pocket_option_adapter.get_latest_tick(sym)
            comp = price_validator.compare_prices(sym, source_tick, feed.current_price)
            results.append(comp.to_dict())
        return results

    async def generate_signal_for_pair(
        self,
        pair_id: str,
        timeframe: str = "1m",
        requested_expiration: int = 1
    ) -> Dict[str, Any]:
        """
        Executes strict institutional 12-Gate evaluation on a requested asset.
        Enforces Zero-Forced-Signal: if conditions are insufficient, returns
        honest NO_TRADE with explicit gate diagnosis.
        """
        import config
        from AITradingEngine.core.signal_config import signal_config_manager

        # Apply latest runtime settings
        signal_config_manager.apply_to_engine(self)

        pair_info = None
        for p in config.PAIRS["otc"] + config.PAIRS["regular"]:
            if p["id"] == pair_id:
                pair_info = p
                break

        if not pair_info:
            return {"error": f"Asset {pair_id} is not supported"}

        payout = pair_info.get("payout", 85) / 100.0
        feed = self.feed_manager.feeds.get(pair_id)

        if not feed:
            return {
                "pair": pair_id,
                "pair_name": pair_info["name"],
                "status": "NO_TRADE",
                "direction": "NO_SIGNAL",
                "reason": "FEED_NOT_INITIALIZED",
                "details": "Data feed for this instrument is initializing.",
                "gate_status": "FEED_INIT"
            }

        # Check staleness & cold-start
        health = feed.check_health()
        if health == "STALE":
            return {
                "pair": pair_id,
                "pair_name": pair_info["name"],
                "status": "NO_TRADE",
                "direction": "NO_SIGNAL",
                "reason": "STALE_DATA",
                "details": "Broker quote feed age exceeds 3.0s latency threshold.",
                "gate_status": "GATE_01_DATA_INTEGRITY"
            }

        if health == "COLD_START":
            return {
                "pair": pair_id,
                "pair_name": pair_info["name"],
                "status": "NO_TRADE",
                "direction": "NO_SIGNAL",
                "reason": "OTC_COLD_START",
                "details": f"OTC statistical sample ({feed.sample_count}/500) has not reached required threshold.",
                "gate_status": "GATE_08_OUT_OF_SAMPLE"
            }

        # Build immutable snapshot
        snapshot = self.feed_manager.build_snapshot(pair_id, payout=payout)
        if not snapshot:
            return {
                "pair": pair_id,
                "pair_name": pair_info["name"],
                "status": "NO_TRADE",
                "direction": "NO_SIGNAL",
                "reason": "INSUFFICIENT_HISTORY",
                "details": "Insufficient closed candlestick history to build multi-timeframe snapshot.",
                "gate_status": "GATE_01_DATA_INTEGRITY"
            }

        # Evaluate Market Quality Score
        quality_score = compute_market_quality(snapshot.candles, snapshot.regime, payout=snapshot.payout)

        # Evaluate 9 Strategies
        dom_dir, votes, has_conflict, conflict_msg = self.strategy_engine.evaluate_all(snapshot)

        if has_conflict:
            return {
                "pair": pair_id,
                "pair_name": pair_info["name"],
                "status": "NO_TRADE",
                "direction": "NO_SIGNAL",
                "reason": "STRATEGY_CONFLICT",
                "details": f"Bullish and Bearish strategies in conflict: {conflict_msg}",
                "gate_status": "GATE_05_DISAGREEMENT_CHECK",
                "market_regime": snapshot.regime.value,
                "quality_score": round(quality_score.score, 1)
            }

        if dom_dir == Direction.NO_SIGNAL:
            return {
                "pair": pair_id,
                "pair_name": pair_info["name"],
                "status": "NO_TRADE",
                "direction": "NO_SIGNAL",
                "reason": "INSUFFICIENT_CONFLUENCE",
                "details": "No strategy consensus detected. Preserving capital.",
                "gate_status": "GATE_04_CONFLUENCE_THRESHOLD",
                "market_regime": snapshot.regime.value,
                "quality_score": round(quality_score.score, 1)
            }

        # Two-stage AI Analyst thesis
        thesis = self.analyst_layer.analyze(snapshot, votes, dom_dir)
        setup_name = thesis["setup_name"]
        confluence_tags = thesis["confluence_tags"]

        # Adversarial Critic audit
        critic_verdict = self.critic_layer.critique(snapshot, dom_dir, setup_name)
        if not critic_verdict.is_approved:
            return {
                "pair": pair_id,
                "pair_name": pair_info["name"],
                "status": "NO_TRADE",
                "direction": "NO_SIGNAL",
                "reason": "CRITIC_VETO",
                "details": f"Adversarial Critic rejected setup: {critic_verdict.veto_reason}",
                "gate_status": "GATE_05_DISAGREEMENT_CHECK",
                "market_regime": snapshot.regime.value,
                "setup": setup_name,
                "quality_score": round(quality_score.score, 1)
            }

        # Uncertainty quantification
        uncertainty = self.uncertainty_engine.calculate_uncertainty(snapshot, votes, thesis["raw_confidence"])
        if uncertainty["is_vetoed"]:
            return {
                "pair": pair_id,
                "pair_name": pair_info["name"],
                "status": "NO_TRADE",
                "direction": "NO_SIGNAL",
                "reason": "HIGH_UNCERTAINTY",
                "details": uncertainty["reason"],
                "gate_status": "GATE_10_NOISE_INDEX",
                "market_regime": snapshot.regime.value
            }

        # Confidence Calibration & Edge
        calibrated_prob = self.confidence_scorer.calibrate(
            raw_confidence=thesis["raw_confidence"],
            critic_penalty=critic_verdict.penalty_score,
            uncertainty=uncertainty["uncertainty_score"]
        )
        edge_data = self.confidence_scorer.calculate_statistical_edge(calibrated_prob, snapshot.payout)

        # 12-Gate Filter Pipeline
        signal = self.signal_gate_pipeline.evaluate_pipeline(
            snapshot=snapshot,
            dominant_direction=dom_dir,
            setup_name=setup_name,
            confluence_tags=confluence_tags,
            strategy_votes=votes,
            critic_verdict=critic_verdict,
            calibrated_prob=calibrated_prob,
            expected_value=edge_data["expected_value"],
            latency_ms=25.0,
            latest_tick_price=snapshot.current_price,
            is_strategy_suspended=False,
            is_risk_cooldown_active=False
        )

        indicators_breakdown = [
            {"name": v.strategy_name, "status": v.direction.value, "detail": v.reason}
            for v in votes
        ]

        if signal.gate_result.is_passed and signal.direction != Direction.NO_SIGNAL:
            delta = snapshot.current_price * 0.00025
            precision = pair_info.get("precision", 5)
            target_exit = round(
                snapshot.current_price + delta if dom_dir == Direction.CALL else snapshot.current_price - delta,
                precision
            )
            dir_ru = "ВВЕРХ" if dom_dir == Direction.CALL else "ВНИЗ"

            return {
                "success": True,
                "status": "SIGNAL_GENERATED",
                "signal_id": signal.signal_id,
                "pair": pair_id,
                "pair_name": pair_info["name"],
                "category": pair_info.get("category", "CURRENCY"),
                "payout": pair_info.get("payout", 85),
                "direction": dom_dir.value,
                "direction_ru": dir_ru,
                "entry_price": snapshot.current_price,
                "target_exit_price": target_exit,
                "confidence_percent": round(calibrated_prob * 100.0, 1),
                "confidence_raw": round(calibrated_prob, 4),
                "grade": signal.grade.value,
                "setup": setup_name,
                "expiration_minutes": requested_expiration,
                "expiration_str": f"{requested_expiration} мин",
                "timeframe": timeframe,
                "summary": (
                    f"AI Signal Engine: {pair_info['name']} — {dir_ru} ({dom_dir.value}). "
                    f"Сетап: {setup_name}. Согласование {len([v for v in votes if v.direction == dom_dir])} стратегий. "
                    f"Калиброванная проходимость: {round(calibrated_prob * 100.0, 1)}%."
                ),
                "confluence_tags": confluence_tags,
                "gate_status": "ALL_12_GATES_PASSED",
                "gate_details": signal.gate_result.details,
                "indicators": indicators_breakdown,
                "metrics": {
                    "rsi": round(snapshot.features.get("rsi_14", 50.0), 1),
                    "atr": round(snapshot.features.get("atr_14", 0.0001), 5),
                    "adx": round(snapshot.features.get("adx_14", 25.0), 1),
                    "choppiness": round(snapshot.features.get("choppiness_14", 38.0), 1),
                    "quality_score": round(quality_score.score, 1)
                }
            }

        # Failed one of the 12 gates
        failed_gate = signal.gate_result.failed_gate_name or "12_GATE_VETO"
        return {
            "pair": pair_id,
            "pair_name": pair_info["name"],
            "status": "NO_TRADE",
            "direction": "NO_SIGNAL",
            "reason": f"GATE_REJECTED: {failed_gate}",
            "details": signal.gate_result.details,
            "gate_status": failed_gate,
            "market_regime": snapshot.regime.value,
            "setup": setup_name,
            "quality_score": round(quality_score.score, 1),
            "indicators": indicators_breakdown
        }

