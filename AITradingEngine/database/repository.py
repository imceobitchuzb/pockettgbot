import json
import time
import sqlite3
from typing import List, Dict, Any, Optional

from AITradingEngine.database.connection import get_database_connection
from AITradingEngine.core.models import MarketSnapshot, FinalSignal, BacktestMetric
from AITradingEngine.core.enums import MarketType, Timeframe


class QuantRepository:
    """Institutional SQLite repository for snapshots, signals, and audits."""

    def __init__(self, conn: Optional[sqlite3.Connection] = None, db_path: Optional[str] = None):
        self._custom_conn = conn
        self._db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        if self._custom_conn:
            return self._custom_conn
        return get_database_connection(self._db_path)


    def save_snapshot(self, snapshot: MarketSnapshot) -> None:
        conn = self._get_conn()
        close_on_finish = self._custom_conn is None
        try:
            candles_serialized = json.dumps([c.to_dict() for c in snapshot.candles[-40:]])
            indicators_serialized = json.dumps(snapshot.indicators)
            
            conn.execute("""
                INSERT OR REPLACE INTO market_snapshots
                (snapshot_id, timestamp, asset, market_type, timeframe, current_price, candles_json, indicators_json, market_regime, volatility_atr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{snapshot.symbol}_{int(snapshot.timestamp)}",
                snapshot.timestamp,
                snapshot.symbol,
                snapshot.market_type.value,
                snapshot.primary_timeframe.value,
                snapshot.current_price,
                candles_serialized,
                indicators_serialized,
                snapshot.regime.value,
                snapshot.indicators.get("atr", 0.0)
            ))
            conn.commit()
        finally:
            if close_on_finish:
                conn.close()

    def save_signal(self, signal: FinalSignal) -> None:
        conn = self._get_conn()
        close_on_finish = self._custom_conn is None
        try:
            conn.execute("""
                INSERT OR REPLACE INTO signals
                (signal_id, snapshot_id, timestamp, asset, market_type, direction, expiration_seconds,
                 quality_grade, confidence, market_regime, primary_strategy, confirming_strategies,
                 entry_price, exit_price, result, payout, pnl, created_at, valid_until, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.signal_id,
                f"{signal.symbol}_{int(signal.timestamp)}",
                signal.timestamp,
                signal.symbol,
                signal.market_type.value,
                signal.direction.value,
                signal.expiration_seconds,
                signal.grade.value,
                signal.confidence,
                "TREND",
                signal.setup_name,
                json.dumps(signal.confluence_tags),
                signal.entry_price,
                signal.entry_price,
                "PENDING",
                0.85,
                0.0,
                signal.timestamp,
                signal.timestamp + signal.expiration_seconds,
                "VALID"
            ))
            conn.commit()
        finally:
            if close_on_finish:
                conn.close()

    def log_rejection(self, asset: str, market_type: str, failed_gate: str, reasons: List[str], metrics: Dict[str, Any]) -> None:
        conn = self._get_conn()
        close_on_finish = self._custom_conn is None
        try:
            conn.execute("""
                INSERT INTO rejection_logs
                (timestamp, asset, market_type, failed_gate, reasons_json, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                int(time.time()),
                asset,
                market_type,
                failed_gate,
                json.dumps(reasons, ensure_ascii=False),
                json.dumps(metrics)
            ))
            conn.commit()
        finally:
            if close_on_finish:
                conn.close()

    def save_rejection(self, symbol: str, gate_name: str, reason: str, snapshot_data: Optional[Dict[str, Any]] = None) -> None:
        """Helper alias for log_rejection."""
        self.log_rejection(
            asset=symbol,
            market_type="OTC" if "OTC" in symbol else "REAL",
            failed_gate=gate_name,
            reasons=[reason],
            metrics=snapshot_data or {}
        )

    def update_signal_outcome(self, signal_id: str, exit_price: float, result: str, pnl: float) -> None:
        conn = self._get_conn()
        close_on_finish = self._custom_conn is None
        try:
            conn.execute("""
                UPDATE signals
                SET exit_price = ?, result = ?, pnl = ?, status = 'COMPLETED'
                WHERE signal_id = ?
            """, (exit_price, result, pnl, signal_id))
            conn.commit()
        finally:
            if close_on_finish:
                conn.close()

    def get_recent_rejections(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        close_on_finish = self._custom_conn is None
        try:
            cur = conn.execute("""
                SELECT timestamp, asset, market_type, failed_gate, reasons_json, metrics_json
                FROM rejection_logs
                ORDER BY log_id DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            results = []
            for r in rows:
                reasons = json.loads(r["reasons_json"]) if r["reasons_json"] else []
                results.append({
                    "timestamp": r["timestamp"],
                    "symbol": r["asset"],
                    "asset": r["asset"],
                    "market_type": r["market_type"],
                    "gate_name": r["failed_gate"],
                    "failed_gate": r["failed_gate"],
                    "reason": reasons[0] if reasons else "Rejected",
                    "reasons": reasons,
                    "metrics": json.loads(r["metrics_json"]) if r["metrics_json"] else {}
                })
            return results
        finally:
            if close_on_finish:
                conn.close()

    def get_recent_signals(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        close_on_finish = self._custom_conn is None
        try:
            cur = conn.execute("""
                SELECT * FROM signals
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]
        finally:
            if close_on_finish:
                conn.close()

    def get_active_signals(self) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        close_on_finish = self._custom_conn is None
        try:
            cur = conn.execute("""
                SELECT * FROM signals
                WHERE status = 'VALID' AND result = 'PENDING'
                ORDER BY timestamp DESC
            """)
            return [dict(row) for row in cur.fetchall()]
        finally:
            if close_on_finish:
                conn.close()


EngineRepository = QuantRepository
quant_repository = QuantRepository()
