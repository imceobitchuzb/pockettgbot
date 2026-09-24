"""
AITradingEngine Multi-Timeframe Feed Manager.
Maintains synchronized candlestick series across canonical boundaries:
5s, 15s, 30s, 1m, 5m, 15m.
Guarantees clean boundary closures without future leakages, enforces strict tick validation,
tracks cold-start sample thresholds, and prevents cross-contamination between OTC and Real markets.
"""
import time
import math
import logging
from typing import Dict, List, Any, Optional

from AITradingEngine.core.enums import MarketType, Timeframe
from AITradingEngine.core.models import Candle, MarketSnapshot
from AITradingEngine.market_data.snapshot_builder import SnapshotBuilder
from AITradingEngine.market_data.pocket_option_adapter import pocket_option_adapter, NormalizedTick
from AITradingEngine.market_data.price_validator import price_validator, ValidationResult
import config

logger = logging.getLogger("AITradingEngine.FeedManager")

TF_SECONDS = {
    Timeframe.S5: 5,
    Timeframe.S15: 15,
    Timeframe.S30: 30,
    Timeframe.M1: 60,
    Timeframe.M5: 300,
    Timeframe.M15: 900
}

OTC_MIN_COLD_START_SAMPLES = 500


class SymbolFeed:
    """Manages candles, tick validation, and cold-start state for a single symbol."""
    def __init__(self, symbol: str, market_type: MarketType = MarketType.OTC, precision: int = 5, base_price: float = 1.0):
        self.symbol = symbol
        self.market_type = market_type
        self.precision = precision
        self.current_price = base_price
        self.last_tick: Optional[NormalizedTick] = None
        self.last_tick_time = time.time()
        self.status = "LIVE"  # "LIVE", "STALE", "COLD_START"
        self.sample_count = 0
        self.is_cold_start_ready = False
        self.timeframe_bars: Dict[Timeframe, List[Candle]] = {
            Timeframe.S5: [],
            Timeframe.S15: [],
            Timeframe.S30: [],
            Timeframe.M1: [],
            Timeframe.M5: [],
            Timeframe.M15: []
        }

    def check_health(self) -> str:
        age = time.time() - self.last_tick_time
        if age > 3.0:
            self.status = "STALE"
        elif not self.is_cold_start_ready and self.market_type == MarketType.OTC:
            self.status = "COLD_START"
        else:
            self.status = "LIVE"
        return self.status


class MultiTFFeedManager:
    """Maintains synchronized multi-timeframe candle feeds for all assets."""

    def __init__(self, repository=None):
        self.repository = repository
        self.feeds: Dict[str, SymbolFeed] = {}
        self.snapshot_builder = SnapshotBuilder()
        self._initialize_from_config()

        # Connect to adapter
        pocket_option_adapter.add_tick_listener(self.on_adapter_tick)

    def _initialize_from_config(self):
        all_pairs = config.PAIRS["otc"] + config.PAIRS["regular"]
        now = int(time.time())

        for p in all_pairs:
            asset = p["id"]
            mtype = MarketType.OTC if "OTC" in asset else MarketType.REAL
            base_price = p.get("base_price", 1.0)
            precision = p.get("precision", 5)

            feed = SymbolFeed(asset, mtype, precision, base_price)
            self.feeds[asset] = feed

            # Generate initial clean 60 1m baseline candles from anchor price
            candles_1m = []
            cur = base_price
            step_size = 0.005 if "JPY" in asset else 0.00005
            for i in range(60):
                t = now - (60 - i) * 60
                o = cur
                delta = math.sin(i * 0.1) * step_size
                c = round(o + delta, precision)
                h = round(max(o, c) + abs(delta * 0.5), precision)
                l = round(min(o, c) - abs(delta * 0.5), precision)
                cur = c
                candles_1m.append(Candle(t, o, h, l, c, 100.0, Timeframe.M1, is_closed=True))

            feed.timeframe_bars[Timeframe.M1] = candles_1m
            feed.sample_count = 60
            feed.is_cold_start_ready = (mtype == MarketType.REAL) or (feed.sample_count >= OTC_MIN_COLD_START_SAMPLES)
            self._build_derived_timeframes(asset)

    def _build_derived_timeframes(self, asset: str):
        if asset not in self.feeds:
            return
        feed = self.feeds[asset]
        candles_1m = feed.timeframe_bars[Timeframe.M1]
        if not candles_1m:
            return

        precision = feed.precision

        # Higher timeframes: 5m, 15m
        for tf, sec in [(Timeframe.M5, 300), (Timeframe.M15, 900)]:
            grouped: Dict[int, List[Candle]] = {}
            for c in candles_1m:
                b = c.timestamp - (c.timestamp % sec)
                if b not in grouped:
                    grouped[b] = []
                grouped[b].append(c)

            tf_candles = []
            for b in sorted(grouped.keys()):
                group = grouped[b]
                tf_candles.append(Candle(
                    timestamp=b,
                    open=group[0].open,
                    high=max(g.high for g in group),
                    low=min(g.low for g in group),
                    close=group[-1].close,
                    volume=sum(g.volume for g in group),
                    timeframe=tf,
                    is_closed=True
                ))
            feed.timeframe_bars[tf] = tf_candles

        # Lower timeframes: 5s, 15s, 30s
        now = int(time.time())
        cur_p = feed.current_price
        step_size = 0.003 if "JPY" in asset else 0.00003

        for tf, sec in [(Timeframe.S5, 5), (Timeframe.S15, 15), (Timeframe.S30, 30)]:
            lower_candles = []
            count = 60
            start_b = now - (now % sec) - (count * sec)
            p = cur_p
            for i in range(count):
                b = start_b + (i * sec)
                o = p
                delta = math.cos(i * 0.15) * step_size
                c = round(o + delta, precision)
                h = round(max(o, c) + abs(delta * 0.4), precision)
                l = round(min(o, c) - abs(delta * 0.4), precision)
                p = c
                lower_candles.append(Candle(b, o, h, l, c, 50.0, tf, is_closed=True))
            feed.timeframe_bars[tf] = lower_candles

    def register_symbol(self, symbol: str, market_type: MarketType = MarketType.OTC, precision: int = 5, base_price: float = 1.0):
        """Registers a symbol in the feed manager if not already present."""
        if symbol not in self.feeds:
            self.feeds[symbol] = SymbolFeed(symbol, market_type, precision, base_price)

    def on_adapter_tick(self, tick: NormalizedTick):
        """Callback from live pocket_option_adapter."""
        self.record_normalized_tick(tick)

    def record_normalized_tick(self, tick: NormalizedTick):
        """Processes normalized tick with full validation & latency gating."""
        if tick.symbol not in self.feeds:
            return

        feed = self.feeds[tick.symbol]

        # 1. Price validation & latency audit
        val_result = price_validator.validate_tick(tick, feed.last_tick)
        if not val_result.is_valid:
            logger.debug(f"Tick rejected for {tick.symbol}: {val_result.rejection_reason}")
            return

        # 2. Update symbol state
        feed.last_tick = tick
        feed.current_price = round(tick.price, feed.precision)
        feed.last_tick_time = time.time()
        feed.sample_count += 1
        if feed.sample_count >= OTC_MIN_COLD_START_SAMPLES or feed.market_type == MarketType.REAL:
            feed.is_cold_start_ready = True
        feed.status = "LIVE"

        # 3. Update canonical candle intervals
        now = int(tick.server_timestamp)
        price = feed.current_price

        for tf, sec in TF_SECONDS.items():
            bucket = now - (now % sec)
            history = feed.timeframe_bars.setdefault(tf, [])

            if not history or history[-1].timestamp < bucket:
                # Close the prior candle
                if history:
                    history[-1] = Candle(
                        timestamp=history[-1].timestamp,
                        open=history[-1].open,
                        high=history[-1].high,
                        low=history[-1].low,
                        close=history[-1].close,
                        volume=history[-1].volume,
                        timeframe=tf,
                        is_closed=True
                    )
                # Open new candle
                new_c = Candle(bucket, price, price, price, price, volume=10.0, timeframe=tf, is_closed=False)
                history.append(new_c)
                if len(history) > 300:
                    history.pop(0)
            else:
                last = history[-1]
                updated_c = Candle(
                    timestamp=last.timestamp,
                    open=last.open,
                    high=max(last.high, price),
                    low=min(last.low, price),
                    close=price,
                    volume=round(last.volume + 1.0, 1),
                    timeframe=tf,
                    is_closed=False
                )
                history[-1] = updated_c

    def record_tick(self, asset: str, price: float):
        """Legacy helper: wraps raw float price into NormalizedTick."""
        if asset not in self.feeds:
            return
        tick = pocket_option_adapter.normalize_raw_tick(symbol=asset, price=price)
        self.record_normalized_tick(tick)

    def get_closed_candles(self, asset: str, tf: Timeframe = Timeframe.M1, limit: int = 60) -> List[Candle]:
        if asset not in self.feeds or tf not in self.feeds[asset].timeframe_bars:
            return []

        all_candles = self.feeds[asset].timeframe_bars[tf]
        now = int(time.time())
        sec = TF_SECONDS.get(tf, 60)
        current_forming_bucket = now - (now % sec)

        closed = [c for c in all_candles if c.timestamp < current_forming_bucket or c.is_closed]
        return closed[-limit:]

    def get_candles(self, asset: str, tf: Timeframe = Timeframe.M1) -> List[Candle]:
        if asset not in self.feeds or tf not in self.feeds[asset].timeframe_bars:
            return []
        return list(self.feeds[asset].timeframe_bars[tf])

    def get_current_price(self, asset: str) -> float:
        if asset in self.feeds:
            return self.feeds[asset].current_price
        return 0.0

    def calibrate_asset_price(self, asset: str, target_price: float):
        """Allows explicit broker quote alignment without drifting history."""
        if asset not in self.feeds:
            return
        feed = self.feeds[asset]
        target_price = round(target_price, feed.precision)
        diff = target_price - feed.current_price
        feed.current_price = target_price

        for tf, bars in feed.timeframe_bars.items():
            for i in range(len(bars)):
                c = bars[i]
                feed.timeframe_bars[tf][i] = Candle(
                    c.timestamp,
                    round(c.open + diff, feed.precision),
                    round(c.high + diff, feed.precision),
                    round(c.low + diff, feed.precision),
                    round(c.close + diff, feed.precision),
                    c.volume,
                    c.timeframe,
                    c.is_closed
                )

    def build_snapshot(self, asset: str, payout: float = 0.85) -> Optional[MarketSnapshot]:
        if asset not in self.feeds:
            return None
        feed = self.feeds[asset]

        # Enforce cold-start requirements for OTC
        if feed.market_type == MarketType.OTC and not feed.is_cold_start_ready:
            logger.warning(f"Cannot build snapshot: OTC asset {asset} is still in cold-start ({feed.sample_count}/{OTC_MIN_COLD_START_SAMPLES})")
            return None

        # Check staleness
        if feed.check_health() == "STALE":
            logger.warning(f"Cannot build snapshot: Feed for {asset} is STALE (> 3s)")
            return None

        candles_1m = self.get_closed_candles(asset, Timeframe.M1, limit=60)
        if not candles_1m or len(candles_1m) < 15:
            return None

        mtf_dict = {
            "5m": self.get_closed_candles(asset, Timeframe.M5, limit=20),
            "15s": self.get_closed_candles(asset, Timeframe.S15, limit=20)
        }

        return self.snapshot_builder.build_snapshot(
            symbol=asset,
            market_type=feed.market_type,
            primary_candles=candles_1m,
            primary_tf=Timeframe.M1,
            mtf_candles=mtf_dict,
            payout=payout
        )


FeedManager = MultiTFFeedManager
feed_manager = MultiTFFeedManager()
