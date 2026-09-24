"""
Technical Analysis Package.
"""
from AITradingEngine.technical_analysis.trend import (
    calc_sma, calc_ema, calc_macd, calc_adx,
    calculate_sma, calculate_ema, calculate_macd, calculate_adx,
    analyze_price_structure
)
from AITradingEngine.technical_analysis.momentum import (
    calc_rsi, calc_stochastic, calc_roc, calc_vortex, calc_aroon
)
from AITradingEngine.technical_analysis.volatility import (
    calc_atr, calc_bollinger_bands,
    calculate_atr, calculate_bollinger_bands,
    detect_volatility_regime
)
from AITradingEngine.technical_analysis.mtf_engine import MTFConcordanceEngine

__all__ = [
    "calc_sma", "calc_ema", "calc_macd", "calc_adx",
    "calculate_sma", "calculate_ema", "calculate_macd", "calculate_adx",
    "analyze_price_structure",
    "calc_rsi", "calc_stochastic", "calc_roc", "calc_vortex", "calc_aroon",
    "calc_atr", "calc_bollinger_bands",
    "calculate_atr", "calculate_bollinger_bands",
    "detect_volatility_regime",
    "MTFConcordanceEngine"
]
