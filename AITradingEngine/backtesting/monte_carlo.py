"""
Monte Carlo Simulation Engine.
Reshuffles trade sequence over 1,000 runs to test robustness and drawdown risk distribution.
"""
import random
from typing import List, Dict, Any


def run_monte_carlo(
    outcomes: List[int],
    num_simulations: int = 1000,
    payout: float = 0.85,
    bet_size: float = 10.0,
    initial_capital: float = 1000.0
) -> Dict[str, Any]:
    """
    Performs Monte Carlo bootstrap permutations.
    """
    if len(outcomes) < 10:
        return {"error": "Need at least 10 trades for Monte Carlo simulation"}

    max_drawdowns = []
    final_equities = []

    for _ in range(num_simulations):
        shuffled = list(outcomes)
        random.shuffle(shuffled)

        equity = initial_capital
        peak = equity
        max_dd = 0.0

        for o in shuffled:
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

        max_drawdowns.append(max_dd)
        final_equities.append(equity)

    max_drawdowns.sort()
    final_equities.sort()

    p95_index = int(num_simulations * 0.95)
    median_index = int(num_simulations * 0.50)
    p5_index = int(num_simulations * 0.05)

    return {
        "simulations_count": num_simulations,
        "median_max_drawdown": round(max_drawdowns[median_index], 2),
        "worst_5pct_drawdown": round(max_drawdowns[p95_index], 2),
        "median_final_equity": round(final_equities[median_index], 2),
        "worst_5pct_equity": round(final_equities[p5_index], 2),
        "risk_of_ruin_pct": round(sum(1 for eq in final_equities if eq <= 0.5 * initial_capital) / num_simulations * 100.0, 2)
    }
