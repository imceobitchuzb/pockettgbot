"""
OTC Market Data Provider.
Strictly isolated provider for Over-The-Counter (OTC) quotation pools.
Never mixes interbank feeds with OTC feeds.
Enforces verified stream ingestion. If stream is not verified/active,
flags status as UNVERIFIED or OFFLINE and refuses to synthesize fake data.
"""
import time
import logging
from typing import Dict, List, Optional, Any

from AITradingEngine.core.enums import MarketType, Timeframe
from AITradingEngine.core.models import Candle
from AITradingEngine.market_data.provider_interface import MarketDataProvider

logger = logging.getLogger("AITradingEngine.OTCMarketDataProvider")


class OTCMarketDataProvider(MarketDataProvider):
    """Dedicated provider for proprietary broker OTC instruments."""

    def __init__(self, min_cold_start_samples: int = 120, max_stale_seconds: float = 3.0):
        self.min_cold_start_samples = min_cold_start_samples
        self.max_stale_seconds = max_stale_seconds
        self.prices: Dict[str, float] = {}
        self.timestamps: Dict[str, float] = {}
        self.sample_counts: Dict[str, int] = {}
        self.is_stream_authenticated: Dict[str, bool] = {}
        self.ticks_history: Dict[str, List[Dict[str, Any]]] = {}
        self.candles_history: Dict[str, Dict[Timeframe, List[Candle]]] = {}

    def get_provider_name(self) -> str:
        return "POCKET_OPTION_OTC_PROVIDER"

    def get_market_type(self) -> MarketType:
        return MarketType.OTC

    def register_symbol(self, symbol: str, is_authenticated_stream: bool = False):
        """Registers an OTC instrument without creating synthetic candles."""
        if symbol not in self.candles_history:
            self.candles_history[symbol] = {
                Timeframe.M1: [],
                Timeframe.M3: [],
                Timeframe.M5: [],
                Timeframe.M15: []
            }
            self.ticks_history[symbol] = []
            self.sample_counts[symbol] = 0
            self.is_stream_authenticated[symbol] = is_authenticated_stream

    def ingest_broker_tick(self, symbol: str, price: float, timestamp: float, volume: float = 100.0, is_verified: bool = True):
        """Ingests verified OTC tick from broker websocket gateway."""
        if symbol not in self.candles_history:
            self.register_symbol(symbol, is_authenticated_stream=is_verified)

        self.is_stream_authenticated[symbol] = is_verified
        self.prices[symbol] = price
        self.timestamps[symbol] = timestamp
        self.sample_counts[symbol] = self.sample_counts.get(symbol, 0) + 1

        if symbol not in self.ticks_history:
            self.ticks_history[symbol] = []
        self.ticks_history[symbol].append({
            "timestamp": timestamp,
            "price": price,
            "volume": volume,
            "verified": is_verified
        })
        if len(self.ticks_history[symbol]) > 500:
            self.ticks_history[symbol].pop(0)

        # Update 1M candle bar
        self._update_otc_candle_bar(symbol, Timeframe.M1, 60, price, timestamp, volume)

    def _update_otc_candle_bar(self, symbol: str, tf: Timeframe, tf_seconds: int, price: float, timestamp: float, volume: float):
        bucket_time = int(timestamp // tf_seconds) * tf_seconds
        bars = self.candles_history[symbol][tf]

        if not bars or bars[-1].timestamp < bucket_time:
            if bars:
                bars[-1].is_closed = True
                self._roll_otc_higher_timeframes(symbol, bars[-1])
            new_bar = Candle(
                timestamp=bucket_time,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                timeframe=tf,
                is_closed=False
            )
            bars.append(new_bar)
            if len(bars) > 300:
                bars.pop(0)
        else:
            cur = bars[-1]
            cur.high = max(cur.high, price)
            cur.low = min(cur.low, price)
            cur.close = price
            cur.volume += volume

    def _roll_otc_higher_timeframes(self, symbol: str, closed_1m: Candle):
        """Rolls closed OTC 1M bars into 3M, 5M, 15M closed bars without look-ahead."""
        for tf, tf_sec in [(Timeframe.M3, 180), (Timeframe.M5, 300), (Timeframe.M15, 900)]:
            bars = self.candles_history[symbol].get(tf, [])
            bucket = (closed_1m.timestamp // tf_sec) * tf_sec

            if not bars or bars[-1].timestamp < bucket:
                if bars:
                    bars[-1].is_closed = True
                new_bar = Candle(
                    timestamp=bucket,
                    open=closed_1m.open,
                    high=closed_1m.high,
                    low=closed_1m.low,
                    close=closed_1m.close,
                    volume=closed_1m.volume,
                    timeframe=tf,
                    is_closed=False
                )
                bars.append(new_bar)
                if len(bars) > 150:
                    bars.pop(0)
            else:
                cur = bars[-1]
                cur.high = max(cur.high, closed_1m.high)
                cur.low = min(cur.low, closed_1m.low)
                cur.close = closed_1m.close
                cur.volume += closed_1m.volume

    async def get_ticks(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self.ticks_history.get(symbol, [])[-limit:]

    async def get_candles(self, symbol: str, timeframe: Timeframe = Timeframe.M1, limit: int = 100) -> List[Candle]:
        symbol_bars = self.candles_history.get(symbol, {})
        bars = symbol_bars.get(timeframe, [])
        closed_bars = [b for b in bars if b.is_closed]
        return closed_bars[-limit:]

    def get_current_price(self, symbol: str) -> float:
        return self.prices.get(symbol, 0.0)

    def get_timestamp(self, symbol: str) -> float:
        return self.timestamps.get(symbol, 0.0)

    def get_market_status(self, symbol: str) -> Dict[str, Any]:
        last_t = self.timestamps.get(symbol, 0.0)
        age = time.time() - last_t if last_t > 0 else 999999.0
        is_verified = self.is_stream_authenticated.get(symbol, False)
        closed_candles = len([b for b in self.candles_history.get(symbol, {}).get(Timeframe.M1, []) if b.is_closed])
        samples = self.sample_counts.get(symbol, 0)

        if not is_verified:
            status_str = "UNVERIFIED"
            is_usable = False
        elif age > self.max_stale_seconds:
            status_str = "STALE"
            is_usable = False
        elif samples < self.min_cold_start_samples:
            status_str = "COLD_START"
            is_usable = False
        else:
            status_str = "LIVE"
            is_usable = (closed_candles >= 30)

        return {
            "provider": self.get_provider_name(),
            "market_type": self.get_market_type().value,
            "status": status_str,
            "latency_ms": round(age * 1000.0, 1),
            "last_update_sec_ago": round(age, 2),
            "samples_collected": samples,
            "min_samples_required": self.min_cold_start_samples,
            "closed_candles_count": closed_candles,
            "is_verified_feed": is_verified,
            "is_usable_for_trading": is_usable
        }
