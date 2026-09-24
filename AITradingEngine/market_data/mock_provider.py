"""
Mock Market Data Provider.
Permitted EXCLUSIVELY for unit tests, offline backtesting, and development simulation.
Strictly prohibited from production live signal generation.
"""
import os
import time
import math
import logging
from typing import Dict, List, Optional, Any

from AITradingEngine.core.enums import MarketType, Timeframe
from AITradingEngine.core.models import Candle
from AITradingEngine.market_data.provider_interface import MarketDataProvider

logger = logging.getLogger("AITradingEngine.MockMarketDataProvider")


class MockMarketDataProvider(MarketDataProvider):
    """Synthetic provider intended solely for deterministic testing and backtest simulation."""

    def __init__(self, allow_in_prod: bool = False):
        is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"
        if is_prod and not allow_in_prod:
            raise RuntimeError(
                "CRITICAL SECURITY VIOLATION: MockMarketDataProvider cannot be initialized in PRODUCTION environment. "
                "Production signal engine must only use verified Real or OTC market data providers."
            )
        self.prices: Dict[str, float] = {}
        self.timestamps: Dict[str, float] = {}
        self.candles_history: Dict[str, Dict[Timeframe, List[Candle]]] = {}
        logger.warning("[MOCK_PROVIDER] Initialized for testing/backtesting ONLY. DO NOT USE IN PRODUCTION.")

    def get_provider_name(self) -> str:
        return "MOCK_TEST_PROVIDER"

    def get_market_type(self) -> MarketType:
        return MarketType.REAL

    def inject_candles(self, symbol: str, timeframe: Timeframe, candles: List[Candle]):
        """Injects deterministic candles for test fixtures."""
        if symbol not in self.candles_history:
            self.candles_history[symbol] = {}
        self.candles_history[symbol][timeframe] = list(candles)
        if candles:
            self.prices[symbol] = candles[-1].close
            self.timestamps[symbol] = candles[-1].timestamp

    async def get_ticks(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        price = self.prices.get(symbol, 100.0)
        t = self.timestamps.get(symbol, time.time())
        return [{"timestamp": t, "price": price, "volume": 100.0}]

    async def get_candles(self, symbol: str, timeframe: Timeframe = Timeframe.M1, limit: int = 100) -> List[Candle]:
        bars = self.candles_history.get(symbol, {}).get(timeframe, [])
        return bars[-limit:]

    def get_current_price(self, symbol: str) -> float:
        return self.prices.get(symbol, 0.0)

    def get_timestamp(self, symbol: str) -> float:
        return self.timestamps.get(symbol, time.time())

    def get_market_status(self, symbol: str) -> Dict[str, Any]:
        return {
            "provider": self.get_provider_name(),
            "market_type": self.get_market_type().value,
            "status": "MOCK_TEST_ONLY",
            "latency_ms": 0.0,
            "last_update_sec_ago": 0.0,
            "closed_candles_count": len(self.candles_history.get(symbol, {}).get(Timeframe.M1, [])),
            "is_usable_for_trading": False  # Never usable for live trading
        }
