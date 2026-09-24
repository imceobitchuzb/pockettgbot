-- AITradingEngine SQLite Schema with WAL mode

CREATE TABLE IF NOT EXISTS market_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    asset TEXT NOT NULL,
    market_type TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    current_price REAL NOT NULL,
    candles_json TEXT NOT NULL,
    indicators_json TEXT NOT NULL,
    market_regime TEXT NOT NULL,
    volatility_atr REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    asset TEXT NOT NULL,
    market_type TEXT NOT NULL,
    direction TEXT NOT NULL,
    expiration_seconds INTEGER NOT NULL,
    quality_grade TEXT NOT NULL,
    confidence REAL NOT NULL,
    market_regime TEXT NOT NULL,
    primary_strategy TEXT NOT NULL,
    confirming_strategies TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    result TEXT DEFAULT 'PENDING',
    payout REAL NOT NULL,
    pnl REAL DEFAULT 0.0,
    created_at INTEGER NOT NULL,
    valid_until INTEGER NOT NULL,
    status TEXT DEFAULT 'VALID',
    FOREIGN KEY(snapshot_id) REFERENCES market_snapshots(snapshot_id)
);

CREATE TABLE IF NOT EXISTS rejection_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    asset TEXT NOT NULL,
    market_type TEXT NOT NULL,
    failed_gate TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_metrics (
    strategy_id TEXT NOT NULL,
    market_type TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    sample_size INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    win_rate REAL NOT NULL DEFAULT 0.0,
    profit_factor REAL NOT NULL DEFAULT 0.0,
    expectancy REAL NOT NULL DEFAULT 0.0,
    max_drawdown REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    last_updated INTEGER NOT NULL,
    PRIMARY KEY (strategy_id, market_type, timeframe)
);

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
