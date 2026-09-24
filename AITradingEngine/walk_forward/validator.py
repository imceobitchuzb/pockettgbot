"""
Walk-Forward Validation Engine.
Splits historical market data into In-Sample (60%), Validation (20%), and Out-Of-Sample (20%) segments.
Ensures models demonstrate genuine statistical edge out-of-sample and flags overfitting.
"""
from typing import List, Dict, Any
from AITradingEngine.core.enums import MarketType, Timeframe
from AITradingEngine.core.models import Candle
from AITradingEngine.backtesting.simulator import BacktestSimulator


class WalkForwardValidator:
    """Walk-Forward Cross-Validation across time partitions."""

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
        self.simulator = BacktestSimulator(symbol, market_type, timeframe, payout)

    def validate(self, candles: List[Candle]) -> Dict[str, Any]:
        """
        Executes Walk-Forward validation.
        """
        total = len(candles)
        if total < 200:
            return {"is_valid": False, "reason": "Insufficient candles for walk-forward validation (min 200)"}

        # 60% In-Sample, 20% Validation, 20% Out-Of-Sample
        split1 = int(total * 0.60)
        split2 = int(total * 0.80)

        in_sample = candles[:split1]
        validation = candles[split1:split2]
        out_of_sample = candles[split2:]

        res_in = self.simulator.run(in_sample)
        res_val = self.simulator.run(validation)
        res_oos = self.simulator.run(out_of_sample)

        m_in = res_in.get("metrics")
        m_val = res_val.get("metrics")
        m_oos = res_oos.get("metrics")

        # Criterion: Out-of-sample must have positive expectancy and win rate >= 55%
        oos_passed = m_oos and m_oos.expectancy > 0.02 and m_oos.win_rate >= 55.0

        return {
            "is_valid": bool(oos_passed),
            "in_sample_trades": m_in.total_trades if m_in else 0,
            "in_sample_win_rate": m_in.win_rate if m_in else 0.0,
            "validation_win_rate": m_val.win_rate if m_val else 0.0,
            "out_of_sample_win_rate": m_oos.win_rate if m_oos else 0.0,
            "out_of_sample_expectancy": m_oos.expectancy if m_oos else 0.0,
            "overfit_detected": (m_in and m_oos and (m_in.win_rate - m_oos.win_rate) > 15.0),
            "decision": "PASSED_OOS" if oos_passed else "REJECTED_OOS_DEGRADATION"
        }
