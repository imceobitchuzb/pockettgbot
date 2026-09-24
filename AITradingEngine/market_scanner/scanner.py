"""
Autonomous Market Scanner.
Monitors configured assets 24/7 across OTC and Real markets.
Evaluates market quality, filters out noisy/choppy conditions, and dynamically
switches focus to the highest-edge instrument.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Callable, Awaitable
from AITradingEngine.core.enums import MarketType, SystemState, QualityGrade, Direction
from AITradingEngine.core.models import MarketSnapshot, MarketQualityScore, FinalSignal
from AITradingEngine.market_data.feed_manager import FeedManager
from AITradingEngine.market_data.snapshot_builder import SnapshotBuilder
from AITradingEngine.regime_detection.regime_detector import RegimeDetector
from AITradingEngine.market_scanner.quality_ranker import compute_market_quality
from AITradingEngine.market_scanner.opportunity_queue import OpportunityQueue

logger = logging.getLogger("AITradingEngine.Scanner")


class MarketScanner:
    """Continuous 24/7 Multi-Market Autonomous Scanner."""

    def __init__(
        self,
        feed_manager: FeedManager,
        pipeline_callback: Optional[Callable[[MarketSnapshot, MarketQualityScore], Awaitable[Optional[FinalSignal]]]] = None,
        scan_interval_sec: float = 3.0
    ):
        self.feed_manager = feed_manager
        self.pipeline_callback = pipeline_callback
        self.scan_interval_sec = scan_interval_sec
        self.regime_detector = RegimeDetector()
        self.opportunity_queue = OpportunityQueue(min_tradable_score=65.0)

        self.current_state = SystemState.SCANNING
        self.current_focus_asset: Optional[str] = None
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self.last_scan_results: Dict[str, Dict] = {}

    def get_tracked_symbols(self) -> List[str]:
        """Returns all symbols currently registered in feed manager."""
        return list(self.feed_manager.feeds.keys())

    async def scan_once(self) -> Dict[str, Dict]:
        """
        Executes a single multi-market scan sweep across all active symbols.
        Returns evaluation summary.
        """
        symbols = self.get_tracked_symbols()
        if not symbols:
            return {"status": "NO_SYMBOLS_REGISTERED", "tradable_count": 0}

        ranked_items = []
        summary = {}

        for symbol in symbols:
            snapshot = self.feed_manager.build_snapshot(symbol, payout=0.85)
            if not snapshot:
                continue

            # Update regime detection
            candles = snapshot.candles or self.feed_manager.get_candles(symbol, snapshot.primary_timeframe)
            regime, details = self.regime_detector.detect(candles)

            # Recalculate snapshot with detected regime
            updated_snap = MarketSnapshot(
                symbol=snapshot.symbol,
                market_type=snapshot.market_type,
                timestamp=snapshot.timestamp,
                current_price=snapshot.current_price,
                primary_timeframe=snapshot.primary_timeframe,
                regime=regime,
                candles=snapshot.candles,
                mtf_candles=snapshot.mtf_candles,
                indicators=snapshot.indicators,
                mtf_alignment=snapshot.mtf_alignment,
                payout=snapshot.payout
            )

            score = compute_market_quality(candles, regime, payout=snapshot.payout)
            ranked_items.append((updated_snap, score))

            summary[symbol] = {
                "market_type": snapshot.market_type.value,
                "regime": regime.value,
                "score": score.total_score,
                "is_tradable": score.is_tradable,
                "notes": score.notes
            }

        self.opportunity_queue.update(ranked_items)
        self.last_scan_results = summary

        # Check top opportunity
        best = self.opportunity_queue.get_top_candidate()
        if best:
            best_snap, best_score = best
            self.current_focus_asset = best_snap.symbol
            self.current_state = SystemState.ANALYZING
            logger.info(
                f"[SCANNER] Optimal candidate identified: {best_snap.symbol} "
                f"({best_snap.market_type.value}) - Score: {best_score.total_score} | Regime: {best_snap.regime.value}"
            )

            # Invoke signal pipeline if registered
            if self.pipeline_callback:
                try:
                    await self.pipeline_callback(best_snap, best_score)
                except Exception as e:
                    logger.error(f"[SCANNER] Pipeline callback error: {e}", exc_info=True)
        else:
            self.current_focus_asset = None
            self.current_state = SystemState.NO_TRADE
            logger.debug("[SCANNER] No market satisfies strict institutional tradability criteria (Zero-Forced-Signal).")

        return summary

    async def start(self) -> None:
        """Starts 24/7 background scanning loop."""
        if self._is_running:
            return
        self._is_running = True
        logger.info("[SCANNER] Autonomous 24/7 Multi-Market Scanner started.")

        async def _loop():
            while self._is_running:
                try:
                    await self.scan_once()
                except Exception as e:
                    logger.error(f"[SCANNER] Exception during scan loop: {e}", exc_info=True)
                await asyncio.sleep(self.scan_interval_sec)

        self._task = asyncio.create_task(_loop())

    async def stop(self) -> None:
        """Stops background scanning loop."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.current_state = SystemState.PAUSED
        logger.info("[SCANNER] Multi-Market Scanner stopped.")
