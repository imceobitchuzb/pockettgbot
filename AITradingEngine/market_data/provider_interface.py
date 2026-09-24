"""
Unified Market Data Provider Interface.
Abstract base class and contract for all real-time and historical market data sources.
Enforces strict provider separation between Real Interbank, OTC Synthetic, and Test Mock providers.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from AITradingEngine.core.enums import MarketType, Timeframe
from AITradingEngine.core.models import Candle


class MarketDataProvider(ABC):
    """Abstract base class for all market data providers."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns provider identifier name."""
        pass

    @abstractmethod
    def get_market_type(self) -> MarketType:
        """Returns the market classification (REAL or OTC)."""
        pass

    @abstractmethod
    async def get_ticks(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns recent tick stream for symbol."""
        pass

    @abstractmethod
    async def get_candles(self, symbol: str, timeframe: Timeframe, limit: int = 100) -> List[Candle]:
        """Returns closed historical candlestick series."""
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """Returns latest verified quote price."""
        pass

    @abstractmethod
    def get_timestamp(self, symbol: str) -> float:
        """Returns epoch timestamp of latest received tick."""
        pass

    @abstractmethod
    def get_market_status(self, symbol: str) -> Dict[str, Any]:
        """
        Returns provider health status:
        - status: "LIVE", "DELAYED", "OFFLINE", "UNVERIFIED"
        - latency_ms: quote latency in milliseconds
        - last_update_sec_ago: seconds since last verified quote
        - is_usable_for_trading: boolean flag
        """
        pass
