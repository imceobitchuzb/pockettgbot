# AUDIT_BEFORE_REBUILD.md
**Comprehensive Pre-Rebuild Technical Forensic Audit**
**Target Repository:** `https://github.com/imceobitchuzb/pockettgbot`
**Audit Date:** 2026-09-24 | **Mode:** Full Codebase Static & Dynamic Inspection

---

## 1. Executive Summary

A comprehensive forensic audit of the entire repository has been performed prior to any architectural modifications. The system was found to be structurally divided into two conflicting layers:
1. **Legacy Mock Sandbox (`engine/`, `test_system.py`, legacy UI endpoints)**: An early prototype that generates prices and candles using `random.gauss`, `math.sin`, hardcoded base prices, and pixel color counting with hardcoded "90%+" claims.
2. **Institutional Quant Engine (`AITradingEngine/`)**: A well-structured framework that was nonetheless contaminated by synthetic candle seeding in `bot.py` and `feed_manager.py`, and bypassed by the Web UI.

The system cannot deliver genuine trading intelligence in its current state because **the signals are calculated on pseudo-random mathematical noise rather than authenticated market data**.

---

## 2. Answers to the 24 Audit Inquiries

| # | Audit Item | Findings & Exact Source |
|---|---|---|
| **1** | **Market Data Origin** | Synthetically generated in `engine/market_data.py:157-165` via `random.gauss` and anchor-pull equations. In `main.py:34-41`, `market_tick_loop` wraps these fake ticks as `POCKET_OPTION_LIVE_STREAM` and feeds them to `AITradingEngine.feed_manager`. |
| **2** | **OTC Prices Origin** | Hardcoded initial prices in `config.py:23-33` (e.g. AUD/CHF OTC: 0.66147, USD/JPY OTC: 157.642). Intraday ticks are synthesized locally via Gaussian noise. There is zero connection to Pocket Option OTC backend pools. |
| **3** | **REAL Prices Origin** | Anchored to public REST endpoints: `api.binance.com/api/v3/ticker/price?symbol=BTCUSDT` (BTC only) and `open.er-api.com/v6/latest/USD` (daily fiat exchange rates, updated once per 24 hours). Sub-second ticks are locally randomized. |
| **4** | **Candle Construction** | Locally bucketed in memory based on system clock modulo 60. Pre-seeded with 60 flat candles in `bot.py:38-79` and sine-wave candles in `feed_manager.py:91-105`. |
| **5** | **Real Historical Sampling** | **NONE**. The system makes zero calls to retrieve historical OHLCV candles from Pocket Option or any institutional market data provider. |
| **6** | **Synthetic / Fake Candles** | **YES**. Heavily prevalent across `bot.py:38-79` (`base_p` ± 0.0002), `feed_manager.py:91-105` (`math.sin`), `feed_manager.py:129-132` (`math.cos`), and `engine/market_data.py:79-88` (`random.gauss`). |
| **7** | **Indicator Calculation** | Duplicated across two engines: `engine/indicators.py` (legacy ZigZag, SAR, Vortex, RSI, Aroon) and `AITradingEngine/technical_analysis/` (modern EMA, MACD, RSI, ATR, Bollinger, ADX, Aroon, Stochastic, MTF). |
| **8** | **BUY/SELL Decisions** | Legacy: `engine/brain.py:240-247` (`bullish_score >= bearish_score` => BUY else SELL). Modern: `AITradingEngine/strategy_engine/engine.py:43-75` (9 strategy votes filtered by 12-Gate pipeline). |
| **9** | **Confidence Calculation** | Legacy: `engine/brain.py:256` (`0.62 + dominant/100 * 0.18`), and `engine/vision_analyzer.py:100` (hardcoded 89.5%–96.0%). Modern: `AITradingEngine/confidence_engine/confidence_scorer.py` (Platt sigmoid calibration). |
| **10** | **Expiration Formation** | `AITradingEngine/signal_engine/expiration_optimizer.py` selects 1m, 2m, 3m, 5m based on noise and regime, but Web UI allows arbitrary manual overrides. |
| **11** | **Entry Price Formation** | Drawn directly from `snapshot.current_price` (which is synthetic tick price) or `feed_manager.get_current_price(pair_id)`. |
| **12** | **Screenshot Analysis** | `engine/vision_analyzer.py` calculates green vs red pixels in cropped regions and forces BUY/SELL with 89–96% confidence. `AITradingEngine/screenshot_analyzer/vision_quant.py` adds image anomaly checks but still lacks robust OCR for symbol and price text. |
| **13** | **Telegram Integration** | `bot.py` uses `aiogram 3.4.0`. Seeds fake candles on startup, provides `/scan`, `/status`, `/perf`, `/debug`, and handles photo uploads. |
| **14** | **Web UI Integration** | `main.py` serves `static/index.html`. Connects to legacy endpoints `/api/price`, `/api/candles`, `/api/history` reading from `engine/market_data.py`, bypassing the new `AITradingEngine` data structures. |
| **15** | **Duplicated Modules** | `engine/market_data.py` vs `AITradingEngine/market_data/feed_manager.py`; `engine/brain.py` vs `AITradingEngine/strategy_engine/`; `engine/indicators.py` vs `AITradingEngine/technical_analysis/`; `engine/history.py` vs `AITradingEngine/database/repository.py`. |
| **16** | **Remaining Legacy Modules** | The entire `engine/` package (`brain.py`, `history.py`, `indicators.py`, `market_data.py`, `vision_analyzer.py`), `test_system.py`. |
| **17** | **Unused Functions** | `market_manager.calibrate_price`, unqueried `AdminMetricsManager`, duplicate in-memory history tracking. |
| **18** | **Hardcoded Values** | `config.py:23-43` base prices; `engine/vision_analyzer.py:100` 89.5%–96.0% confidence; `feed_manager.py:94` step sizes; `pocket_option_adapter.py:167` 15ms ping. |
| **19** | **Race Conditions** | Background tick task mutates `SymbolFeed.timeframe_bars` in-place while scanner reads it concurrently without locking. |
| **20** | **Stale Prices** | Tick loop continuously generates synthetic ticks even when external APIs fail, concealing disconnection from the user. |
| **21** | **Repainting & Look-Ahead** | Legacy `engine/indicators.py` ZigZag looks ahead at future bars. Unclosed candles used in some technical indicators without explicit bar closure verification. |
| **22** | **Substitution of Real with Fake** | `main.py:38-41` explicitly stamps synthetic ticks as `source="POCKET_OPTION_LIVE_STREAM"`. Fake sine candles seeded into real feed buffers. |
| **23** | **Incorrect Win/Loss Stats** | `history_manager.check_active_signals` resolves outcomes using locally randomized ticks rather than real broker prices. |
| **24** | **Unfounded Confidence Claims** | "90%+ Accuracy" claims across README, UI headers, and legacy brain violates statistical truth and binary options mathematics. |

---

## 3. Vulnerability Classification

### 🔴 CRITICAL
1. **Pervasive Synthetic Market Data**: The engine evaluates strategies on `random.gauss` and `math.sin` data, producing completely illusory trading signals.
2. **Deceptive Source Labeling**: `main.py` labels synthetic ticks as `POCKET_OPTION_LIVE_STREAM`.
3. **Startup Fake-Candle Injection**: `bot.py:38-79` preseeds 60 flat bars based on `base_price` into `feed_manager`.
4. **Zero-Connection Adapter**: `pocket_option_adapter.py` reports `is_connected = True` and synthesizes fake pings without opening a network socket.
5. **Architectural Schism**: Telegram and Web UI route through conflicting legacy and modern engines.

### 🟠 HIGH
1. **Unsubstantiated 90%+ Accuracy Marketing**: Pervasive claims in README and UI mislead users.
2. **Missing OCR in Vision Analysis**: Screenshot analyzer infers signals from color ratios without verified OCR of symbol, timeframe, and price digits.
3. **ZigZag Look-Ahead Bias**: Legacy indicator inspects future data points to identify pivots.
4. **Arbitrary Expiration Selection**: Lack of volatility-calibrated expiration models for 1M/2M/3M/5M expiries.
5. **No Concurrency Protection**: Multi-timeframe bar lists lack mutex/lock protection against concurrent mutation during scans.

### 🟡 MEDIUM
1. **Uncalibrated Platt Parameters**: Sigmoid scaling parameters `platt_a` and `platt_b` are theoretical constants rather than fitted from empirical backtest logs.
2. **Unverified OTC Quotes**: OTC prices treated as parallel to interbank without broker quotation stream.
3. **In-Memory Volatile History**: Trade results in `engine/history.py` are lost upon server restart.
4. **Duplicate Indicator Calculation**: Computational waste running both legacy and modern indicators.

### 🟢 LOW
1. **Missing Typing and Docstrings in Legacy Code**.
2. **Static Asset Caching**: Static files lack cache-busting hashes in `index.html`.
3. **Hardcoded UI Port**: Localhost port 8000 assumptions in Telegram WebApp button.

---

## 4. Architectural Rebuild Plan (Phases 1–30)

```
[Real / OTC Market Data Providers] 
               │
               ▼
       [DataQualityGate] ──(FAIL)──► [NO TRADE: Insufficient/Corrupt Data]
               │ (PASS)
               ▼
     [Candle & MTF Builder] (Strictly Closed Bars: 1M, 3M, 5M, 15M)
               │
               ▼
      [Analytical Engine]
    ┌──────────┼──────────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼          ▼
 [Trend]  [Momentum] [Volatility] [Price]  [Structure]
 (EMA/ADX) (RSI/MACD)  (ATR/BB)   (Action)  (S/R Levels)
    └──────────┼──────────┴──────────┴──────────┘
               ▼
     [Market Regime Engine] (Trend, Range, Breakout, Extreme Volatility)
               │
               ▼
   [Confluence Scoring (0-100)] (Evidence, NOT Win Probability)
               │
               ▼
     [Hard NO-TRADE Filters] (Choppiness, MTF Disagreement, Stale, High Risk)
               │
               ▼
   [Signal Object / Lifecycle] (CREATED -> VALIDATED -> SENT -> ACTIVE -> RESOLVED)
               │
       ┌───────┴───────┐
       ▼               ▼
 [Telegram Bot]   [Modern Dark Web UI]
```

**Next Action:** Proceed immediately to Phase 1 (Delete fictitious market data) through Phase 30.
