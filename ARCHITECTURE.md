# ARCHITECTURE.md: Autonomous Multi-Market Signal Intelligence System

**System Name**: Ultimate AI Signal Engine (`AITradingEngine/`)  
**Target Platform**: Pocket Option (Real Markets & OTC Markets)  
**Core Directive**: *Zero-Forced-Signal Policy & Quantitative Edge Verification*  
**Core Axiom**: **NO TRADE IS A VALID DECISION.**

---

## 1. CURRENT SYSTEM ANALYSIS

### 1.1 Architecture & Components
- **Framework**: FastAPI (v0.141.1) serving REST endpoints and WebSocket (`/ws/live`), with an integrated `aiogram 3.28.2` Telegram bot (`bot.py`).
- **Data Layer (`engine/market_data.py`)**:
  - In-memory tick generator aligned to 60s boundaries.
  - Generates 1m candles and aggregates to 2m, 3m, 5m.
  - Background async loop attempts to pull base exchange rates from `api.binance.com` and `open.er-api.com`.
  - **Limitations**: No sub-minute timeframes (5s, 15s, 30s), no 15m macro timeframe. No multi-market ranker. No data quality auditing (missing candles, timestamp skew, abnormal jumps).
- **Analytical Layer (`engine/brain.py`)**:
  - Monolithic `AnalystBrain` evaluates 8 hardcoded indicator weights.
  - Sums weights into `bullish_score` vs `bearish_score`.
  - Forces an output: always returns either `BUY` or `SELL`.
  - Confidence is scaled via a linear formula (`88.0 + (score/100)*8.0 + random`) rather than statistical expectancy.
  - **Limitations**: No isolated strategies, no concept of `NO SIGNAL`, no market regime detection (Choppy, Volatile, Trend, Range), no conflict detection between indicators.
- **Persistence (`engine/history.py`)**:
  - In-memory Python `list` initialized with hardcoded seed trades.
  - Volatile: all data is erased when the process restarts.
  - **Limitations**: No SQLite/PostgreSQL, no trade audit logs, no snapshot archiving, no statistical significance tracking.
- **Vision Analyzer (`engine/vision_analyzer.py`)**:
  - Pillow image analyzer sampling green/red pixels in chart region and oscillator region.
  - Outputs dictionary with direction and confidence.
  - **Limitations**: No anomaly detection (corrupted image, missing timestamps, fake scaling), no fallback to `signal: false, reason: "INSUFFICIENT_DATA"`.
- **Telegram Bot (`bot.py`)**:
  - Simple command handlers `/signal`, `/otc`, `/stats` that trigger `analyst_brain` and send a message.
  - Hardcoded to single pair or fixed expiration.

---

## 2. PROPOSED SYSTEM ARCHITECTURE

The new architecture introduces **`AITradingEngine/`**, designed as an institutional-grade, multi-layered quant system:

```
c:\Users\user\Documents\tgbot\
├── AITradingEngine/
│   ├── __init__.py
│   ├── core/
│   │   ├── enums.py                # Direction (CALL, PUT, NO_SIGNAL), MarketType (OTC, REAL), QualityGrade (A, B, NO_TRADE), SystemState
│   │   ├── models.py               # Immutable Dataclasses: Candle, MarketSnapshot, StrategyVote, FinalSignal, MarketQualityScore
│   │   └── exceptions.py           # Engine specific exceptions (DataQualityError, FilterRejection, etc.)
│   ├── market_data/
│   │   ├── feed_manager.py         # Multi-TF Feed (5s, 15s, 30s, 1m, 5m, 15m) for all available pairs
│   │   ├── data_cleaner.py         # Outlier rejection, gap detection, timestamp integrity, staleness checker
│   │   ├── snapshot_builder.py     # Immutable Market Snapshot (strictly closed candles, ZERO look-ahead bias)
│   │   └── latency_monitor.py      # Tracking data, analysis, and network latency (<350ms threshold)
│   ├── market_scanner/
│   │   ├── scanner.py              # 24/7 background scanner evaluating all OTC & Real pairs
│   │   ├── quality_ranker.py       # Computes Market Quality Score (0-100) per asset
│   │   └── opportunity_queue.py    # Priority queue selecting only top candidate setups
│   ├── regime_detection/
│   │   ├── regime_detector.py      # ML & Quant classifier: TREND_UP, TREND_DOWN, RANGE, BREAKOUT, REVERSAL, CHOPPY, UNSTABLE
│   │   └── noise_filter.py         # Statistical noise detector (Chop Index, ATR/Range ratio) -> Forces NO TRADE on Choppy
│   ├── technical_analysis/
│   │   ├── trend.py                # EMA (9, 21, 50, 200), SMA, MACD, ADX (trend strength), Price Structure (HH, HL, LH, LL)
│   │   ├── momentum.py             # RSI, Stochastic (%K, %D), ROC, Momentum
│   │   ├── volatility.py           # ATR, Bollinger Bands (Squeeze vs Expansion), Volatility Regimes
│   │   └── mtf_engine.py           # Multi-Timeframe Alignment (5m Macro -> 1m Structure -> 15s/30s Entry)
│   ├── pattern_engine/
│   │   ├── price_action.py         # Dynamic S/R zones, Rejection wicks, Pin bar, Engulfing, Inside bar
│   │   └── liquidity.py            # Liquidity sweeps, False breakouts (Fakeouts), Range boundaries
│   ├── strategy_engine/
│   │   ├── base_strategy.py        # Abstract base class: evaluate(snapshot) -> StrategyVote
│   │   ├── registry.py             # Dynamic strategy registry & lifecycle manager (ACTIVE, UNDER_REVIEW, SUSPENDED)
│   │   ├── strategies/
│   │   │   ├── s01_trend_following.py
│   │   │   ├── s02_trend_pullback.py
│   │   │   ├── s03_sr_rejection.py
│   │   │   ├── s04_breakout_confirm.py
│   │   │   ├── s05_false_breakout.py
│   │   │   ├── s06_momentum_pulse.py
│   │   │   ├── s07_mean_reversion.py
│   │   │   ├── s08_volatility_regime.py
│   │   │   └── s09_mtf_confluence.py
│   │   └── conflict_detector.py    # Disagreement Detector: if opposing strong signals emerge -> CONFLICT -> NO TRADE
│   ├── ai_ensemble/
│   │   ├── analyst_layer.py        # AI #1: Generates setup thesis, directional bias, and confidence
│   │   ├── critic_layer.py         # AI #2 (Conservative Devil's Advocate): Actively seeks falsification reasons
│   │   ├── ml_scorer.py            # Calibrated probability model (Logistic/Tree/Bayesian ensemble with Brier score verification)
│   │   └── uncertainty_engine.py   # Measures prediction entropy/variance. High uncertainty -> NO TRADE
│   ├── confidence_engine/
│   │   ├── confidence_scorer.py    # Non-arbitrary Bayesian confidence combining agreement, edge, regime & sample size
│   │   └── quality_grader.py       # Grades signal: GRADE A (Institutional), GRADE B (Standard), NO TRADE
│   ├── signal_engine/
│   │   ├── signal_gate.py          # 12-Step strict pipeline: Data, Regime, MTF, Confluence, Edge, Noise, Payout, Cooldown
│   │   ├── expiration_optimizer.py # Selects 15s, 30s, 1m, 2m, 3m, 5m based on backtested out-of-sample edge
│   │   ├── pre_signal_recheck.py   # Re-fetches fresh market data at t-0 immediately before dispatch
│   │   └── invalidation.py         # Checks if price drifted past entry or setup invalidated -> CANCEL
│   ├── risk_engine/
│   │   ├── anti_overtrading.py     # Strict per-asset cooldown timers and max signals/hour
│   │   ├── loss_streak_shield.py   # Tracks consecutive losses, raises confidence threshold or triggers pause
│   │   ├── duplicate_guard.py      # Prevents identical/concurrent signals on the same asset
│   │   └── emergency_shutdown.py   # Circuit breaker: halts engine upon abnormal data, latency spikes, or drawdowns
│   ├── otc_engine/
│   │   ├── otc_dataset.py          # Isolated OTC data storage and micro-tick models
│   │   ├── otc_regime.py           # Specialized OTC regime classification
│   │   └── otc_edge.py             # Independent OTC performance statistics
│   ├── real_market_engine/
│   │   ├── real_dataset.py         # Interbank forex/crypto data feed
│   │   ├── session_filter.py       # Session awareness (London, NY, Asian overlap)
│   │   └── real_edge.py            # Independent Real Market performance statistics
│   ├── screenshot_analyzer/
│   │   ├── vision_quant.py         # Structured Vision AI with strict JSON schema
│   │   └── anomaly_detector.py     # Detects fake/edited screenshots, abnormal scaling, or blurred history
│   ├── backtesting/
│   │   ├── simulator.py            # Discrete-event & vectorized backtester (payout, slippage, execution latency)
│   │   ├── metrics.py              # Win rate, Expectancy, Profit Factor, Max Drawdown, Kelly/fractional statistics
│   │   └── monte_carlo.py          # Monte Carlo permutations to evaluate sequence risk and drawdown distribution
│   ├── walk_forward/
│   │   ├── split_manager.py        # Train (60%), Validation (20%), Out-Of-Sample (20%) partitioning
│   │   ├── walk_forward_runner.py  # Rolling walk-forward testing
│   │   └── drift_detector.py       # Concept Drift Detection: flags performance degradation and suspends failing strategies
│   ├── database/
│   │   ├── connection.py           # SQLite connection with WAL (Write-Ahead Logging) & foreign keys
│   │   ├── schema.sql              # Relational schema for snapshots, signals, executions, strategy performance
│   │   └── repository.py           # Type-safe repository methods
│   ├── monitoring/
│   │   ├── system_state.py         # Engine states: SCANNING, ANALYZING, VALIDATING, SIGNAL_READY, NO_TRADE, PAUSED
│   │   └── admin_metrics.py        # Aggregates real-time health, latency, strategy winrates, and rejection logs
│   └── logging/
│       └── quant_logger.py         # Structured JSON logging of every decision, filter rejection, and snapshot ID
```

---

## 3. DATA FLOW

```
[Live Feed / Public APIs / OTC Stream]
       │
       ▼
[Data Cleaner] ──(Checks timestamps, gaps, abnormal jumps, staleness)
       │ (Reject if corrupt)
       ▼
[Feed Manager] ──(Constructs synchronized multi-timeframe candles: 5s, 15s, 30s, 1m, 5m, 15m)
       │
       ▼
[Snapshot Builder] ──(Captures immutable snapshot of CLOSED candles only at t0 -> Zero look-ahead bias)
       │
       ├──────────────────────────────────────────┐
       ▼                                          ▼
[SQLite DB: market_snapshots]             [Market Scanner & Regime Detector]
```

1. **Ingestion**: Market ticks arrive from OTC generator or real market API.
2. **Sanitization**: `DataCleaner` rejects data if latency > 350ms, gaps are found, or unrealistic price jumps occur.
3. **Multi-Timeframe Aggregation**: Candlesticks are aggregated synchronously across 6 timeframes (`5s`, `15s`, `30s`, `1m`, `5m`, `15m`).
4. **Immutable Snapshot**: When analysis begins, an immutable `MarketSnapshot` is instantiated. It contains strictly completed candles up to `timestamp - 1ms`. Future candles cannot be queried.

---

## 4. AI & ENSEMBLE FLOW

```
              ┌───────────────────────────┐
              │      Market Snapshot      │
              └─────────────┬─────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          ▼                                   ▼
[AI #1: Analyst Layer]              [AI #2: Critic Layer (Adversarial)]
  - Evaluates 9 strategies            - Ignores Analyst's thesis
  - Computes MTF Confluence           - Specifically searches for invalidations
  - Computes Technical Scores         - Checks noise, choppy regime, high spread
  - Proposes: Direction + Setup       - Flags: Weaknesses, Rejection warnings
          │                                   │
          └─────────────────┬─────────────────┘
                            ▼
               [Strategy Conflict Detector]
               - Checks for opposing directional signals
               - If Conflict > Threshold ──► [FORCE: NO TRADE]
                            │
                            ▼
              [Uncertainty & Calibration Engine]
              - Measures Brier-calibrated probability
              - If Uncertainty == HIGH ──► [FORCE: NO TRADE]
                            │
                            ▼
               [Ensemble Consensus Vector]
```

---

## 5. MACHINE LEARNING (ML) FLOW

1. **Feature Engineering (`feature_pipeline.py`)**:
   - Calculates 42 stationary statistical features: Log returns, normalized candle body/wicks, ATR ratios, ADX trend strength, RSI distance from 50, Bollinger %B, MACD histogram velocity, S/R zone distance, higher timeframe slope.
   - Strictly normalized without future leakages.
2. **Model Ensemble**:
   - Primary: LightGBM / Calibrated Logistic Regressor trained on Walk-Forward out-of-sample windows.
   - Auxiliary: Vision AI for visual chart geometry confirmation.
3. **Probability Calibration**:
   - Raw classifier probabilities pass through Platt Scaling / Isotonic Regression.
   - Brier score and calibration curves are continuously tracked in `database/`.
4. **Uncertainty Rejection**:
   - If model variance or entropy exceeds tolerance, the prediction is categorized as `HIGH UNCERTAINTY` and suppressed.

---

## 6. SIGNAL PIPELINE & THE 12-GATE FILTER

Every potential opportunity must pass through the **Signal Gate** in sequence:

```
[Candidate Setup from Scanner]
       │
       ▼
Gate 01: [Data Integrity Check]       ── FAIL ──► [LOG: REJECT_DATA_QUALITY]
       ▼ PASS
Gate 02: [Market Regime Check]        ── FAIL (Choppy/Unstable) ──► [LOG: REJECT_MARKET_CHOP]
       ▼ PASS
Gate 03: [Multi-Timeframe Agreement]  ── FAIL (Conflicting 5m vs 15s) ──► [LOG: REJECT_MTF_CONFLICT]
       ▼ PASS
Gate 04: [Strategy Confluence >= 3]   ── FAIL (< 3 confirming strats) ──► [LOG: REJECT_LOW_CONFLUENCE]
       ▼ PASS
Gate 05: [Disagreement Check]         ── FAIL (Opposing strategy votes) ──► [LOG: REJECT_STRATEGY_CONFLICT]
       ▼ PASS
Gate 06: [Historical Edge & Sample]   ── FAIL (OOS Expectancy <= 0 or N < 50) ──► [LOG: REJECT_NO_STATISTICAL_EDGE]
       ▼ PASS
Gate 07: [Walk-Forward Status]        ── FAIL (Strategy SUSPENDED) ──► [LOG: REJECT_STRATEGY_SUSPENDED]
       ▼ PASS
Gate 08: [Volatility & Noise Check]   ── FAIL (Noise index > 0.65) ──► [LOG: REJECT_MARKET_NOISE]
       ▼ PASS
Gate 09: [Payout Filter]              ── FAIL (Payout < 80%) ──► [LOG: REJECT_LOW_PAYOUT]
       ▼ PASS
Gate 10: [Anti-Overtrading & Cooldown]── FAIL (Asset in cooldown) ──► [LOG: REJECT_COOLDOWN_ACTIVE]
       ▼ PASS
Gate 11: [Consecutive Loss Shield]    ── FAIL (Threshold raised due to drawdown) ──► [LOG: REJECT_DRAWDOWN_SHIELD]
       ▼ PASS
Gate 12: [Pre-Signal Live Recheck]    ── FAIL (Price shifted or pattern broken) ──► [LOG: REJECT_PRE_EXECUTION_DRIFT]
       ▼ PASS
[DISPATCH SIGNAL: GRADE A or GRADE B]
```

If **any single gate fails**, the engine issues **`NO SIGNAL`** and writes a structured rejection log.

---

## 7. DATABASE SCHEMA (SQLite with WAL Mode)

```sql
-- Snapshots table: Full market state at moment of decision
CREATE TABLE IF NOT EXISTS market_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    asset TEXT NOT NULL,
    market_type TEXT NOT NULL, -- 'OTC' or 'REAL'
    timeframe TEXT NOT NULL,
    current_price REAL NOT NULL,
    candles_json TEXT NOT NULL,
    indicators_json TEXT NOT NULL,
    market_regime TEXT NOT NULL,
    volatility_atr REAL NOT NULL
);

-- Signals table: Every approved signal with complete audit trail
CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    asset TEXT NOT NULL,
    market_type TEXT NOT NULL,
    direction TEXT NOT NULL, -- 'CALL' or 'PUT'
    expiration_seconds INTEGER NOT NULL,
    quality_grade TEXT NOT NULL, -- 'GRADE_A' or 'GRADE_B'
    confidence REAL NOT NULL,
    market_regime TEXT NOT NULL,
    primary_strategy TEXT NOT NULL,
    confirming_strategies TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    result TEXT DEFAULT 'PENDING', -- 'WIN', 'LOSS', 'INVALIDATED'
    payout REAL NOT NULL,
    pnl REAL DEFAULT 0.0,
    created_at INTEGER NOT NULL,
    valid_until INTEGER NOT NULL,
    FOREIGN KEY(snapshot_id) REFERENCES market_snapshots(snapshot_id)
);

-- Rejection decisions table: Full logging of NO_SIGNAL decisions
CREATE TABLE IF NOT EXISTS rejection_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    asset TEXT NOT NULL,
    market_type TEXT NOT NULL,
    failed_gate TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL
);

-- Strategy performance stats: Independent tracking for OTC and Real
CREATE TABLE IF NOT EXISTS strategy_metrics (
    strategy_id TEXT NOT NULL,
    market_type TEXT NOT NULL, -- 'OTC' or 'REAL'
    timeframe TEXT NOT NULL,
    sample_size INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    win_rate REAL NOT NULL DEFAULT 0.0,
    profit_factor REAL NOT NULL DEFAULT 0.0,
    expectancy REAL NOT NULL DEFAULT 0.0,
    max_drawdown REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'UNDER_REVIEW', 'SUSPENDED'
    last_updated INTEGER NOT NULL,
    PRIMARY KEY (strategy_id, market_type, timeframe)
);

-- Daily monitoring metrics
CREATE TABLE IF NOT EXISTS monitoring_daily (
    date TEXT PRIMARY KEY,
    total_scans INTEGER NOT NULL DEFAULT 0,
    signals_grade_a INTEGER NOT NULL DEFAULT 0,
    signals_grade_b INTEGER NOT NULL DEFAULT 0,
    no_signals_count INTEGER NOT NULL DEFAULT 0,
    total_pnl REAL NOT NULL DEFAULT 0.0,
    max_consecutive_losses INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms REAL NOT NULL DEFAULT 0.0
);
```

---

## 8. BACKTESTING & WALK-FORWARD ARCHITECTURE

### 8.1 Simulation Realism
- Models discrete execution timestamps, 150ms execution latency, exact broker payout (e.g. 85%), and realistic candle tick path.
- Strictly forbids look-ahead indexing (`i` can only access `data[:i]`).

### 8.2 Walk-Forward Protocol
1. **Train Window (60%)**: Calibrate indicator thresholds and strategy weights.
2. **Validation Window (20%)**: Tune expiration choice (15s, 30s, 1m, 2m, 3m, 5m) and confidence thresholds.
3. **Out-of-Sample Window (20%)**: Final blind forward testing.
4. **Strategy Lifecycle Rules**:
   - If Out-of-Sample Expectancy < 0 or Win Rate < 56.5% (break-even at 85% payout is 54.1%): **SUSPEND STRATEGY**.
   - Minimum sample size requirement: $N \ge 50$ events before a strategy's historical edge vote is considered valid.

### 8.3 Concept Drift Detection
- Rolling 50-trade window comparison against the 500-trade baseline.
- If rolling winrate drops by more than $2.0 \times \sigma$, the strategy is automatically transitioned from `ACTIVE` to `UNDER_REVIEW`.

---

## 9. FAILURE MODES & CIRCUIT BREAKERS

| Failure Mode | Detection Mechanism | Immediate Action |
| :--- | :--- | :--- |
| **API Data Gap / Stale Quotes** | `DataCleaner` detects $\Delta t > 3 \times \text{interval}$ | Rejects asset, flags `DATA_ERROR`. If pervasive, pauses scanner. |
| **Latency Spike (>350ms)** | `LatencyMonitor` measures t_server - t_data | Invalidates current setup, suppresses signal dispatch. |
| **Market Flash Crash / Abnormal Wick** | Spread or single-candle return $> 4.0 \times \text{ATR}$ | Switches regime to `UNSTABLE`, blocks all trading on asset for 15m. |
| **Consecutive Loss Cluster** | 3 consecutive losses on active strategy | Automatically increases minimum confidence threshold from 0.80 to 0.88. |
| **Pervasive Model Anomaly** | Ensemble disagreement entropy $> 0.85$ | Forces `NO TRADE — ALL MARKETS`. |
| **Emergency Shutdown** | System drawdown $> 15\%$ or database corruption | Dispatches Telegram alert `⚠️ ENGINE PAUSED: INTEGRITY SAFEGUARD` and halts. |

---

## 10. SECURITY & COMPLIANCE

1. **No Guaranteed Profit Claims**: All UI, Telegram messages, and logs strictly omit words like "100%", "guaranteed", "sure win", "risk-free". Every signal includes statistical grade and risk disclaimer.
2. **Token & Credential Isolation**: Bot tokens and API credentials stored in `.env` and loaded via `config.py`. Never logged in plain text.
3. **Zero Martingale**: The engine calculates edge and setup validity only. Money management logic enforces strict flat risk sizing.

---

## 11. MONITORING & ADMIN DASHBOARD

The system exposes quantitative health monitoring through REST APIs and Telegram commands:
- `/status`: Engine state (`SCANNING`, `NO_TRADE`, `ACTIVE`), active regime, latency, current asset queue.
- `/perf`: Segregated OTC vs Real Market metrics (Winrate, Expectancy, Sample Size, Drawdown).
- `/debug`: Explains exactly why the last 5 setups were rejected (e.g. `EUR/USD OTC: REJECTED at Gate 05 (Strategy Conflict: Trend CALL vs S/R PUT)`).
- Web Dashboard `/admin`: Visual inspection of strategy lifecycle, Brier score calibration, and Monte Carlo drawdown distribution.

---

## 12. SUMMARY OF COMPONENT RESPONSIBILITIES

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AITradingEngine Core                            │
│                                                                        │
│  [Market Scanner] ──► [Data Cleaner] ──► [Snapshot Builder]            │
│          ▲                                      │                      │
│          │                                      ▼                      │
│  [Anti-Overtrading]                   [Regime & Noise Filter]          │
│          ▲                                      │                      │
│          │                                      ▼                      │
│  [12-Gate Filter] ◄── [Ensemble Engine] ◄── [9 Strategies + MTF]       │
│          │                                                             │
│          ├──► PASS ──► [Format Signal] ──► [Telegram & WebApp]         │
│          │                                                             │
│          └──► FAIL ──► [Log NO_SIGNAL] ──► [SQLite DB Audit]           │
└────────────────────────────────────────────────────────────────────────┘
```
