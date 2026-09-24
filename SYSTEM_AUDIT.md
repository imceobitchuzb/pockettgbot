# SYSTEM AUDIT: POCKET OPTION AI SIGNAL ENGINE & TRADING TERMINAL
**Date**: September 2026  
**Auditor**: Senior Quant & AI Trading Systems Architect  
**Scope**: End-to-end audit of data pipelines, OTC isolation, live market synchronization, signal generation, computer vision screenshot scanner, runtime configuration, and trading terminal UI.

---

## Executive Summary

A comprehensive forensic audit of the codebase revealed critical structural defects that violate institutional trading standards:
1. **Data Fabrication**: Quotes were synthesized using Gaussian random walks (`random.gauss`), and real forex rates were directly copied onto OTC synthetic assets.
2. **Forced Signal Generation**: The engine lacked a true `NO_SIGNAL` / `NO_TRADE` condition, arbitrarily forcing `BUY` or `SELL` and fabricating confidence numbers between 89.0% and 96.0%.
3. **Disconnected Signal Settings**: UI settings adjusted by the user in `static/js/app.js` remained isolated in browser storage and were never transmitted to or honored by the signal engine.
4. **Superficial Computer Vision**: The screenshot scanner relied on raw pixel color threshold counts, hardcoded pair names based on file strings, and lacked candle geometry, OCR, or live market cross-referencing.
5. **Absence of Broker Feed Adapter**: No live WebSocket connection or real-time tick validator existed, causing persistent price desynchronization with Pocket Option.

---

## Detailed Findings Matrix (10 Critical Areas)

### 1. OTC Random Walk & Unsound Signal Generation
* **Current Problem**: OTC pairs produce erratic, baseless signals with synthetic fluctuations that have zero predictive edge.
* **Root Cause**: `engine/market_data.py` lines 83–88 and 157–164 simulate OTC price action using Gaussian random drift (`noise = random.gauss(0, 1) * volatility`). Furthermore, line 224 copies interbank foreign exchange rates directly onto OTC pairs (`self.calibrate_price("USD_JPY_OTC", jpy_p)`), which is financially invalid since OTC feeds in binary options are broker-specific synthetic liquidity pools.
* **Affected File / Module**: `engine/market_data.py`, `AITradingEngine/otc_engine/otc_validator.py`.
* **Proposed Fix**:
  - Strictly isolate OTC data streams from Real Market interbank feeds.
  - Implement an OTC Cold-Start Gate requiring a minimum sample size (>= 500 closed ticks/candles) before any strategy is permitted to evaluate an OTC asset.
  - Reject any signal where OTC volatility or structure fails the statistical randomness test (Runs test / Choppiness Index > 61.8).
* **Test Required**: `test_otc_strict_isolation_and_cold_start()`.

---

### 2. Real Market Signal Reliability & Low-Quality Setups
* **Current Problem**: Real market signals trigger during low-liquidity hours, bank holidays, and choppy sideways markets, leading to severe drawdowns.
* **Root Cause**: `engine/brain.py` evaluated all assets uniformly without session awareness, spread penalties, or multi-timeframe regime filtering. Any marginal difference between `bullish_score` and `bearish_score` triggered a signal.
* **Affected File / Module**: `engine/brain.py`, `AITradingEngine/real_market_engine/market_hours.py`, `AITradingEngine/regime_detection/regime_detector.py`.
* **Proposed Fix**:
  - Enforce real session gating (London/New York overlap vs Asian consolidation vs Weekend closures).
  - Require Multi-Timeframe (MTF) confluence: 5m trend alignment + 1m structure confirmation + 15s/30s entry precision.
  - If regime is detected as `CHOPPY` or `UNSTABLE`, enforce `NO_TRADE`.
* **Test Required**: `test_real_market_session_gating_and_regime_filtering()`.

---

### 3. Price Discrepancy Between Bot and Pocket Option
* **Current Problem**: Displayed quotes on the terminal and Telegram bot deviate significantly from live broker prices on Pocket Option.
* **Root Cause**:
  - `engine/market_data.py` uses independent local time-step random walking that rapidly drifts from real quotes.
  - Periodic sync relied on `https://open.er-api.com/v6/latest/USD`, which has end-of-day update latencies and lacks millisecond tick resolution.
  - `main.py` lines 144–146 hardcoded a static calibration hack (`market_manager.calibrate_price(pair_id, 157.642)`).
* **Affected File / Module**: `engine/market_data.py`, `main.py`, `config.py`.
* **Proposed Fix**:
  - Implement `PocketOptionLiveAdapter` supporting live WebSocket / low-latency streaming quote feeds with automatic heartbeat and reconnection.
  - Provide a Price Comparison Debugger endpoint (`GET /api/debugger/price-comparison`) comparing source feed vs bot feed with delta and latency tracking.
* **Test Required**: `test_pocket_option_adapter_and_price_validator()`.

---

### 4. LIVE / Direct Market Data Synchronization & Latency Gating
* **Current Problem**: Ticks arrive out of order, stale ticks are accepted, and latency spikes are ignored, causing trades to be placed on outdated market states.
* **Root Cause**: No tick validation, timestamp verification, or latency gate existed. Quotes were accepted regardless of how long ago they were generated.
* **Affected File / Module**: `AITradingEngine/market_data/latency_monitor.py`, `AITradingEngine/market_data/data_cleaner.py`.
* **Proposed Fix**:
  - Create `PriceValidator` with strict latency gating: reject any tick where `current_time - server_timestamp > 0.350s`.
  - Mark asset status as `STALE_DATA` whenever feed interval exceeds 3.0s, immediately suspending signal generation.
  - Detect price jumps exceeding 4x ATR as anomalies.
* **Test Required**: `test_latency_gate_and_stale_data_rejection()`.

---

### 5. Non-Functional Signal Parameters (Expiration, Timeframe, Payout)
* **Current Problem**: Selecting different expirations (15s, 30s, 1m, 5m) or timeframes in the UI produced identical scores and failed to adapt strategies.
* **Root Cause**: `engine/brain.py` line 256 trivially echoed `exp_min = requested_expiration if requested_expiration in [1, 2, 3, 5] else 1` without calculating expiration-specific win expectations or volatility horizons.
* **Affected File / Module**: `engine/brain.py`, `AITradingEngine/signal_engine/expiration_optimizer.py`.
* **Proposed Fix**:
  - Integrate `ExpirationOptimizer`: evaluate target expiration suitability against current ATR, candle momentum, and historical setup duration.
  - Validate broker payout (reject any asset where payout < 80% to protect positive mathematical expectation).
* **Test Required**: `test_expiration_optimizer_and_payout_gate()`.

---

### 6. Signal Settings Pipeline Disconnected from Backend Engine
* **Current Problem**: Changing settings (min confidence, confluence count, risk mode, OTC toggle) in the web UI had zero effect on signals generated.
* **Root Cause**: `static/js/app.js` saved settings to browser `localStorage` but never made an HTTP PUT/POST to the server. `main.py` had no endpoints to store or read user settings, and `analyst_brain` had no configuration parameters.
* **Affected File / Module**: `static/js/app.js`, `main.py`, `AITradingEngine/core/signal_config.py`.
* **Proposed Fix**:
  - Create persistent `SignalConfig` dataclass and JSON store (`data/signal_settings.json`).
  - Implement `GET /api/settings`, `POST /api/settings`, and `POST /api/settings/reset`.
  - Dynamically propagate configuration updates into `AITradingEngine` runtime parameters in memory immediately upon save.
* **Test Required**: `test_signal_settings_pipeline_sync()`.

---

### 7. Screenshot Scanner Producing Incorrect Analysis & Guessing
* **Current Problem**: Uploading chart screenshots resulted in hallucinated signals, incorrect pair identification, and fake confidence percentages.
* **Root Cause**:
  - `engine/vision_analyzer.py` line 134 hardcoded the asset name: `"USD/JPY OTC" if "1790077605438" in filename else "AUD/CHF OTC"`.
  - No OCR was performed; the analyzer had no capability to read pair labels, timestamps, or price axes.
  - Always produced a BUY or SELL with 89.5%–96% confidence regardless of image quality.
* **Affected File / Module**: `engine/vision_analyzer.py`, `AITradingEngine/screenshot_analyzer/vision_quant.py`.
* **Proposed Fix**:
  - Build institutional `VisionQuantEngine`:
    1. Image integrity check (resolution, blur, aspect ratio, chart presence).
    2. OCR & metadata extraction (Pair, Timeframe, Broker Price, Expiration).
    3. Live feed cross-reference: compare screenshot price and timestamp with live broker data.
    4. Strict rejection with `{"signal": false, "reason": "INSUFFICIENT_DATA"}` if blurry, missing price, or desynchronized.
* **Test Required**: `test_vision_quant_integrity_and_rejection()`.

---

### 8. Vision AI Lacking Structural Chart Understanding
* **Current Problem**: Vision analyzer treated all green pixels as bullish and red pixels as bearish, ignoring support/resistance levels, trend structures, candle wicks, and oscillator geometry.
* **Root Cause**: Simple pixel color counting loop (`for y in range(y_start, y_end): if g > 110 ...`) in `engine/vision_analyzer.py` lines 58–73.
* **Affected File / Module**: `engine/vision_analyzer.py`, `AITradingEngine/screenshot_analyzer/anomaly_detector.py`.
* **Proposed Fix**:
  - Implement candlestick structure parser (wick-to-body ratios, rejection pinbars, engulfing patterns).
  - Add trendline / horizontal level recognition.
  - Adversarial Critic check on visual setups: if chart shows consolidation at resistance, reject long entries.
* **Test Required**: `test_vision_structural_geometry_parser()`.

---

### 9. Forced Signal Logic & Fake 90%+ Confidence
* **Current Problem**: The system promised 90%+ accuracy and always produced a signal, even in random, unreadable market conditions.
* **Root Cause**:
  - `engine/brain.py` line 235: `if bullish_score >= bearish_score: BUY else SELL`.
  - `engine/brain.py` lines 251–253: `raw_prob = 88.0 + (dominant_score / 100.0) * 8.0; confidence_percent = min(96.0, max(89.0, ...))`.
* **Affected File / Module**: `engine/brain.py`, `AITradingEngine/confidence_engine/confidence_scorer.py`, `AITradingEngine/signal_engine/signal_gate.py`.
* **Proposed Fix**:
  - Purge all forced BUY/SELL branches and synthetic confidence math.
  - Implement Platt-calibrated confidence scoring (sigmoid-calibrated probability mapped to historical win rates: 55%–85%).
  - Enforce 12-Gate Filter Pipeline: any failed gate immediately outputs `NO_SIGNAL` with explicit gate failure diagnostic reason.
* **Test Required**: `test_zero_forced_signal_and_platt_confidence()`.

---

### 10. Terminal UI Lacking Real-Time Stream, Latency Debugging & Responsive Controls
* **Current Problem**: Web terminal had unresponsive buttons, static price tables, no visibility into why signals were rejected, and no data feed latency indicators.
* **Root Cause**: `static/index.html` and `static/js/app.js` were built as static mockups without bi-directional event streaming, WebSocket state reconciliation, or latency monitors.
* **Affected File / Module**: `static/index.html`, `static/css/style.css`, `static/js/app.js`.
* **Proposed Fix**:
  - Redesign into a high-tech dark institutional terminal:
    - Real-time scanner table with live prices, payouts, regimes, and quality grades.
    - Live Terminal Activity Feed streaming real-time gate evaluation logs.
    - Signal Lifecycle Card with honest Platt confidence, countdown timer, and 12-gate audit checklist.
    - Price Comparison / Latency Debugger panel.
    - Working Settings modal dynamically communicating with `/api/settings`.
* **Test Required**: `test_web_api_settings_and_debugger_endpoints()`.

---

## Action Plan & Verification Roadmap

| Phase | Milestone | Deliverable | Status |
|---|---|---|---|
| **Phase 1** | Live Broker Data Pipeline | `pocket_option_adapter.py`, `price_validator.py`, `/api/debugger/price-comparison` | In Progress |
| **Phase 2** | Canonical Candle Engine | Server timestamp aggregation, `LIVE` / `STALE` lifecycle | In Progress |
| **Phase 3** | Signal Settings Architecture | `signal_config.py`, `GET/POST /api/settings`, dynamic engine updates | In Progress |
| **Phase 4** | Purge Random Signals & Enforce Gates | Replace `engine/brain.py`, route `/api/signal/generate` to `AITradingEngine` | In Progress |
| **Phase 5** | Strict OTC Isolation & Cold Start | 500-tick cold start, statistical randomness rejection | In Progress |
| **Phase 6** | Rebuilt Vision Quant Scanner | `vision_quant.py` with OCR, integrity checks, live cross-check | In Progress |
| **Phase 7** | Institutional Terminal UI | Modern dark UI, live activity feed, debugger panel, settings modal | In Progress |
| **Phase 8** | 28 Acceptance Criteria Suite | `test_audit_criteria.py` with 100% PASS verification | Planned |
