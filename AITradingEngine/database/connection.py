import sqlite3
import os
from typing import Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
DEFAULT_DB_PATH = os.path.join(DB_DIR, "quant_engine.db")


def get_database_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = db_path or DEFAULT_DB_PATH
    target_dir = os.path.dirname(target_path)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    conn = sqlite3.connect(target_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high-concurrency non-blocking reads/writes
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn



def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Alias for get_database_connection."""
    return get_database_connection(db_path)


def init_db(db_path: Optional[str] = None, conn: Optional[sqlite3.Connection] = None):
    close_after = False
    if conn is None:
        conn = get_database_connection(db_path)
        close_after = True
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    if close_after:
        conn.close()


# Auto-initialize default database schema on import
init_db()
