import json
import time
import sqlite3
from typing import List, Dict, Any, Optional

from AITradingEngine.database.connection import get_database_connection, init_db
from AITradingEngine.core.models import MarketSnapshot, FinalSignal, BacktestMetric
from AITradingEngine.core.enums import MarketType, Timeframe


class QuantRepository:
    """Institutional SQLite repository for snapshots, signals, and audits."""

    def __init__(self, conn: Optional[sqlite3.Connection] = None, db_path: Optional[str] = None):
        self._custom_conn = conn
        self._db_path = db_path
        try:
            if self._custom_conn is not None:
                init_db(conn=self._custom_conn)
            elif self._db_path is not None:
                init_db(db_path=self._db_path)
        except Exception:
            pass

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

    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Calculates authentic, un-mocked performance metrics (Phase 15)."""
        conn = self._get_conn()
        close_on_finish = self._custom_conn is None
        try:
            cur = conn.execute("""
                SELECT signal_id, timestamp, asset, market_type, direction,
                       expiration_seconds, entry_price, exit_price, result,
                       payout, pnl, market_regime, primary_strategy
                FROM signals
                ORDER BY timestamp ASC
            """)
            rows = [dict(r) for r in cur.fetchall()]

            total_signals = len(rows)
            resolved_trades = [r for r in rows if r["result"] in ("WIN", "LOSS")]
            wins = sum(1 for r in resolved_trades if r["result"] == "WIN")
            losses = sum(1 for r in resolved_trades if r["result"] == "LOSS")
            win_rate = round(wins / len(resolved_trades) * 100.0, 1) if resolved_trades else 0.0

            total_pnl = sum(r["pnl"] for r in resolved_trades)
            gross_profit = sum(r["pnl"] for r in resolved_trades if r["pnl"] > 0)
            gross_loss = abs(sum(r["pnl"] for r in resolved_trades if r["pnl"] < 0))
            profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
            average_result = round(total_pnl / len(resolved_trades), 2) if resolved_trades else 0.0

            # Calculate max consecutive loss streak
            max_streak = 0
            cur_streak = 0
            for r in resolved_trades:
                if r["result"] == "LOSS":
                    cur_streak += 1
                    max_streak = max(max_streak, cur_streak)
                else:
                    cur_streak = 0

            # Breakdowns
            by_asset: Dict[str, int] = {}
            by_market: Dict[str, int] = {}
            by_setup: Dict[str, int] = {}
            by_regime: Dict[str, int] = {}
            by_hour: Dict[int, int] = {}

            for r in rows:
                a = r["asset"]
                by_asset[a] = by_asset.get(a, 0) + 1
                m = r["market_type"]
                by_market[m] = by_market.get(m, 0) + 1
                s = r["primary_strategy"]
                by_setup[s] = by_setup.get(s, 0) + 1
                reg = r["market_regime"]
                by_regime[reg] = by_regime.get(reg, 0) + 1
                hr = time.gmtime(r["timestamp"]).tm_hour
                by_hour[hr] = by_hour.get(hr, 0) + 1

            return {
                "total_signals": total_signals,
                "resolved_trades": len(resolved_trades),
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "total_pnl": round(total_pnl, 2),
                "average_result": average_result,
                "max_losing_streak": max_streak,
                "signals_by_asset": by_asset,
                "signals_by_market_type": by_market,
                "signals_by_setup": by_setup,
                "signals_by_market_regime": by_regime,
                "signals_by_hour": by_hour
            }
        finally:
            if close_on_finish:
                conn.close()


EngineRepository = QuantRepository
quant_repository = QuantRepository()
