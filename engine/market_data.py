import time
import random
import math
import asyncio
import httpx
from typing import Dict, List, Any, Optional
from config import PAIRS

class Candle:
    def __init__(self, timestamp: int, open_p: float, high_p: float, low_p: float, close_p: float, volume: float = 100.0):
        self.timestamp = timestamp
        self.open = open_p
        self.high = high_p
        self.low = low_p
        self.close = close_p
        self.volume = volume

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


class MarketDataManager:
    def __init__(self):
        self.pairs_map: Dict[str, Dict[str, Any]] = {}
        for p in PAIRS["otc"] + PAIRS["regular"]:
            self.pairs_map[p["id"]] = p

        self.candles_history: Dict[str, Dict[str, List[Candle]]] = {}
        self.current_prices: Dict[str, float] = {}
        self.trend_states: Dict[str, Dict[str, Any]] = {}
        self.last_candle_buckets: Dict[str, int] = {}
        self.last_sync_time = 0

        self._initialize_all_pairs()

    def _initialize_all_pairs(self):
        now = int(time.time())
        now_candle_time = now - (now % 60)

        for pair_id, pair_info in self.pairs_map.items():
            base_price = pair_info["base_price"]
            precision = pair_info["precision"]
            self.current_prices[pair_id] = base_price

            # Volatility matched to currency pair scale
            if "JPY" in pair_id:
                volatility = 0.015
            elif "BTC" in pair_id:
                volatility = 15.0
            elif "ETH" in pair_id:
                volatility = 2.0
            elif "GOLD" in pair_id:
                volatility = 0.4
            else:
                volatility = 0.00012

            self.trend_states[pair_id] = {
                "direction": 1 if random.random() > 0.5 else -1,
                "cycles_left": random.randint(12, 28),
                "volatility": volatility,
                "trend_momentum": 0.0,
                "base_anchor": base_price
            }

            self.candles_history[pair_id] = {"1m": [], "2m": [], "3m": [], "5m": []}

            # Generate 90 historical 1m candles aligned to clock minutes
            cur_p = base_price
            history_1m = []
            start_time = now_candle_time - (90 * 60)

            for i in range(90):
                c_time = start_time + (i * 60)
                open_p = cur_p
                # Random drift with slight trend
                delta = (random.gauss(0, 1) * volatility * 1.2)
                close_p = round(open_p + delta, precision)
                high_p = round(max(open_p, close_p) + abs(random.gauss(0, volatility * 0.8)), precision)
                low_p = round(min(open_p, close_p) - abs(random.gauss(0, volatility * 0.8)), precision)
                cur_p = close_p
                history_1m.append(Candle(c_time, open_p, high_p, low_p, close_p, round(random.uniform(120, 650), 1)))

            self.candles_history[pair_id]["1m"] = history_1m
            self.current_prices[pair_id] = cur_p
            self.last_candle_buckets[pair_id] = now_candle_time

            self._rebuild_higher_timeframes(pair_id)

    def _rebuild_higher_timeframes(self, pair_id: str):
        candles_1m = self.candles_history[pair_id]["1m"]
        for tf_min in [2, 3, 5]:
            tf_str = f"{tf_min}m"
            sec = tf_min * 60
            grouped: Dict[int, List[Candle]] = {}
            for c in candles_1m:
                bucket = c.timestamp - (c.timestamp % sec)
                if bucket not in grouped:
                    grouped[bucket] = []
                grouped[bucket].append(c)

            tf_candles = []
            for bucket_time in sorted(grouped.keys()):
                group = grouped[bucket_time]
                o = group[0].open
                c = group[-1].close
                h = max(g.high for g in group)
                l = min(g.low for g in group)
                v = sum(g.volume for g in group)
                tf_candles.append(Candle(bucket_time, o, h, l, c, round(v, 1)))

            self.candles_history[pair_id][tf_str] = tf_candles

    def calibrate_price(self, pair_id: str, target_price: float):
        """Allows instant calibration to match Pocket Option live terminal quote."""
        if pair_id not in self.pairs_map:
            return
        precision = self.pairs_map[pair_id]["precision"]
        target_price = round(target_price, precision)
        diff = target_price - self.current_prices[pair_id]

        self.current_prices[pair_id] = target_price
        self.trend_states[pair_id]["base_anchor"] = target_price

        # Shift recent candles so chart smoothly connects with the calibrated price
        for tf in self.candles_history[pair_id]:
            for c in self.candles_history[pair_id][tf]:
                c.open = round(c.open + diff, precision)
                c.close = round(c.close + diff, precision)
                c.high = round(c.high + diff, precision)
                c.low = round(c.low + diff, precision)

    def tick_pair(self, pair_id: str) -> Dict[str, Any]:
        """Produce live tick strictly synchronized to current clock seconds."""
        if pair_id not in self.pairs_map:
            return {}

        state = self.trend_states[pair_id]
        pair = self.pairs_map[pair_id]
        precision = pair["precision"]
        volatility = state["volatility"]

        # Cycle trend evolution
        state["cycles_left"] -= 1
        if state["cycles_left"] <= 0:
            state["direction"] = -state["direction"] if random.random() > 0.35 else state["direction"]
            state["cycles_left"] = random.randint(15, 40)
            state["trend_momentum"] = random.uniform(0.3, 0.9) * state["direction"]

        # Realistic tick price change
        noise = random.gauss(0, 1) * volatility * 0.35
        trend_pull = state["trend_momentum"] * volatility * 0.25
        
        # Soft pull towards base anchor to avoid runaway drift
        anchor_pull = (state["base_anchor"] - self.current_prices[pair_id]) * 0.015

        tick_delta = noise + trend_pull + anchor_pull
        cur_p = round(self.current_prices[pair_id] + tick_delta, precision)
        self.current_prices[pair_id] = cur_p

        # Real clock alignment (strictly HH:MM:00)
        now = int(time.time())
        candle_bucket = now - (now % 60)
        history_1m = self.candles_history[pair_id]["1m"]

        if not history_1m or candle_bucket > history_1m[-1].timestamp:
            # Complete previous candle and open new candle for current clock minute
            new_candle = Candle(candle_bucket, cur_p, cur_p, cur_p, cur_p, volume=round(random.uniform(10, 35), 1))
            history_1m.append(new_candle)
            if len(history_1m) > 180:
                history_1m.pop(0)
            self._rebuild_higher_timeframes(pair_id)
        else:
            # Update current running candle
            last = history_1m[-1]
            last.close = cur_p
            last.high = max(last.high, cur_p)
            last.low = min(last.low, cur_p)
            last.volume = round(last.volume + random.uniform(2, 8), 1)

        seconds_remaining = 60 - (now % 60)

        return {
            "pair": pair_id,
            "price": cur_p,
            "timestamp": now,
            "seconds_remaining": seconds_remaining,
            "candle": history_1m[-1].to_dict()
        }

    async def sync_with_live_market(self):
        """Fetch real market rates from public exchanges to anchor quotes."""
        now = int(time.time())
        if now - self.last_sync_time < 30: # at most every 30 seconds
            return
        self.last_sync_time = now

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                # 1. Sync Crypto
                try:
                    r_btc = await client.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
                    if r_btc.status_code == 200:
                        btc_p = float(r_btc.json()["price"])
                        self.calibrate_price("BTC_USDT", btc_p)
                        self.calibrate_price("BTC_USD_OTC", btc_p)
                except Exception:
                    pass

                # 2. Sync Forex rates via open API
                try:
                    r_fx = await client.get("https://open.er-api.com/v6/latest/USD")
                    if r_fx.status_code == 200:
                        rates = r_fx.json().get("rates", {})
                        # Strictly Real Market pairs only. OTC pairs must NEVER be overwritten by forex rates!
                        if "JPY" in rates:
                            jpy_p = round(float(rates["JPY"]), 3)
                            self.calibrate_price("USD_JPY", jpy_p)
                        if "EUR" in rates and rates["EUR"] > 0:
                            eur_usd = round(1.0 / float(rates["EUR"]), 5)
                            self.calibrate_price("EUR_USD", eur_usd)
                        if "GBP" in rates and rates["GBP"] > 0:
                            gbp_usd = round(1.0 / float(rates["GBP"]), 5)
                            self.calibrate_price("GBP_USD", gbp_usd)
                except Exception:
                    pass
        except Exception as e:
            print(f"Market sync warning: {e}")

    def get_candles(self, pair_id: str, timeframe: str = "1m", limit: int = 100) -> List[Dict[str, Any]]:
        if pair_id not in self.candles_history:
            return []
        tf_dict = self.candles_history[pair_id]
        candles = tf_dict.get(timeframe, tf_dict.get("1m", []))
        return [c.to_dict() for c in candles[-limit:]]

    def get_current_price(self, pair_id: str) -> float:
        return self.current_prices.get(pair_id, 0.0)

    def get_pair_info(self, pair_id: str) -> Optional[Dict[str, Any]]:
        return self.pairs_map.get(pair_id)

    def get_all_pairs(self) -> Dict[str, List[Dict[str, Any]]]:
        otc = []
        regular = []
        for p in PAIRS["otc"]:
            p_copy = p.copy()
            p_copy["current_price"] = self.get_current_price(p["id"])
            otc.append(p_copy)
        for p in PAIRS["regular"]:
            p_copy = p.copy()
            p_copy["current_price"] = self.get_current_price(p["id"])
            regular.append(p_copy)
        return {"otc": otc, "regular": regular}

market_manager = MarketDataManager()
