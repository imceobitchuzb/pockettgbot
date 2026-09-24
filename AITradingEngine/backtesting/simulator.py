"""
Event-Driven Backtest Simulator.
Steps through historical candle sequences point-in-time, enforcing zero look-ahead bias,
and simulating realistic option outcomes.
"""
from typing import List, Dict, Any, Optional
from AITradingEngine.core.enums import Direction, MarketType, Timeframe
from AITradingEngine.core.models import Candle, BacktestMetric
from AITradingEngine.market_data.snapshot_builder import SnapshotBuilder
from AITradingEngine.strategy_engine.engine import StrategyEngine
from AITradingEngine.backtesting.metrics import calculate_backtest_metrics


class BacktestSimulator:
    """Historical event-driven simulator for quantitative strategies."""

    def __init__(
        self,
        symbol: str = "EURUSD",
        market_type: MarketType = MarketType.REAL,
        timeframe: Timeframe = Timeframe.TF_1M,
        payout: float = 0.85
    ):
        self.symbol = symbol
        self.market_type = market_type
        self.timeframe = timeframe
        self.payout = payout
        self.snapshot_builder = SnapshotBuilder()
        self.strategy_engine = StrategyEngine()

    def run(
        self,
        candles: List[Candle],
        horizon_candles: int = 2,
        min_warmup: int = 50
    ) -> Dict[str, Any]:
        """
        Executes backtest over candle list.
        """
        if len(candles) < min_warmup + horizon_candles + 1:
            return {"error": "Candles insufficient for backtest"}

        outcomes: List[int] = []
        trades_log = []

        # Iterate point-in-time: at step i, only candles[0:i] are known!
        for i in range(min_warmup, len(candles) - horizon_candles):
            historical_slice = candles[:i]
            entry_candle = candles[i - 1]
            entry_price = entry_candle.close

            # Build point-in-time snapshot
            snapshot = self.snapshot_builder.build_snapshot(
                symbol=self.symbol,
                market_type=self.market_type,
                primary_candles=historical_slice,
                primary_tf=self.timeframe,
                payout=self.payout
            )
            if not snapshot:
                continue

            # Evaluate strategies
            dom_dir, votes, has_conflict, _ = self.strategy_engine.evaluate_all(snapshot)

            # Strict policy: skip if no consensus or conflict
            if dom_dir == Direction.NO_SIGNAL or has_conflict:
                continue

            # Simulate outcome at expiration horizon
            expiry_candle = candles[i - 1 + horizon_candles]
            exit_price = expiry_candle.close

            if dom_dir == Direction.CALL:
                if exit_price > entry_price:
                    outcome = 1  # Win
                elif exit_price < entry_price:
                    outcome = -1  # Loss
                else:
                    outcome = 0  # Tie
            else:  # PUT
                if exit_price < entry_price:
                    outcome = 1  # Win
                elif exit_price > entry_price:
                    outcome = -1  # Loss
                else:
                    outcome = 0  # Tie

            outcomes.append(outcome)
            trades_log.append({
                "candle_idx": i,
                "direction": dom_dir.value,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "outcome": outcome
            })

        metrics = calculate_backtest_metrics(outcomes, payout=self.payout)

        return {
            "metrics": metrics,
            "outcomes": outcomes,
            "trades_count": len(outcomes),
            "trades_log": trades_log,
            "trades_sample": trades_log[:10]
        }
