"""
Quantitative Performance Metrics.
Calculates Win Rate, Profit Factor, Expectancy, Max Drawdown, and statistical significance.
"""
import math
from typing import List, Dict, Any
from AITradingEngine.core.models import BacktestMetric


def calculate_backtest_metrics(
    outcomes: List[int],  # 1 for Win, 0 for Tie, -1 for Loss
    payout: float = 0.85,
    initial_capital: float = 1000.0,
    bet_size: float = 10.0
) -> BacktestMetric:
    """
    Computes rigorous metrics from a sequence of trade outcomes.
    """
    total = len(outcomes)
    if total == 0:
        return BacktestMetric(
            total_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            expectancy=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0
        )

    wins = sum(1 for o in outcomes if o == 1)
    losses = sum(1 for o in outcomes if o == -1)
    ties = sum(1 for o in outcomes if o == 0)

    resolved = wins + losses
    win_rate = (wins / resolved * 100.0) if resolved > 0 else 0.0

    gross_profit = wins * (bet_size * payout)
    gross_loss = losses * bet_size
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

    # Expectancy per unit risked:
    p_win = wins / resolved if resolved > 0 else 0.0
    expectancy = (p_win * payout) - ((1.0 - p_win) * 1.0)

    # Equity curve and Max Drawdown calculation
    equity = initial_capital
    peak = equity
    max_dd = 0.0
    returns = []

    for o in outcomes:
        if o == 1:
            pnl = bet_size * payout
        elif o == -1:
            pnl = -bet_size
        else:
            pnl = 0.0

        equity += pnl
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100.0 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
        returns.append(pnl / initial_capital)

    # Sharpe ratio approximation
    if len(returns) > 1:
        mean_ret = sum(returns) / len(returns)
        std_ret = math.sqrt(sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1))
        sharpe = (mean_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0.0
    else:
        sharpe = 0.0

    return BacktestMetric(
        total_trades=total,
        win_rate=round(win_rate, 2),
        profit_factor=round(profit_factor, 2),
        expectancy=round(expectancy, 4),
        max_drawdown=round(max_dd, 2),
        sharpe_ratio=round(sharpe, 2)
    )
