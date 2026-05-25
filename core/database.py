"""
PRIMEngine — Database Backend
================================
SQLite persistence layer for dispatch sessions, results, and usage metrics.
Upgrade to PostgreSQL (via SQLAlchemy) for AWS deployment.

PRIMEnergeia S.A.S.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager


DB_PATH = os.environ.get("PRIMENGINE_DB", os.path.expanduser("~/.prime_api/primengine.db"))


def _ensure_db_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_connection():
    """Thread-safe database connection context manager."""
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS dispatch_sessions (
                session_id TEXT PRIMARY KEY,
                api_key_hash TEXT NOT NULL,
                name TEXT,
                market TEXT NOT NULL,
                fleet_mw REAL NOT NULL,
                status TEXT DEFAULT 'created',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                result_json TEXT
            );

            CREATE TABLE IF NOT EXISTS dispatch_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                api_key_hash TEXT NOT NULL,
                market TEXT NOT NULL,
                fleet_mw REAL,
                duration_hours REAL,
                engine_type TEXT,
                total_fuel_kg REAL,
                fuel_savings_pct REAL,
                dispatch_cost_usd REAL,
                savings_usd REAL,
                solver_time_ms REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES dispatch_sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS usage_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key_hash TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                market TEXT,
                response_ms REAL,
                status_code INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_history_key ON dispatch_history(api_key_hash);
            CREATE INDEX IF NOT EXISTS idx_history_market ON dispatch_history(market);
            CREATE INDEX IF NOT EXISTS idx_usage_key ON usage_metrics(api_key_hash);
        """)


# ─── Session Operations ───

def save_session(session_id: str, api_key_hash: str, name: str,
                 market: str, fleet_mw: float, status: str = "created"):
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO dispatch_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, api_key_hash, name, market, fleet_mw, status, now, now, None)
        )


def update_session_result(session_id: str, status: str, result_dict: dict):
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE dispatch_sessions SET status=?, updated_at=?, result_json=? WHERE session_id=?",
            (status, now, json.dumps(result_dict), session_id)
        )


def get_session(session_id: str, api_key_hash: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM dispatch_sessions WHERE session_id=? AND api_key_hash=?",
            (session_id, api_key_hash)
        ).fetchone()
        return dict(row) if row else None


def list_sessions(api_key_hash: str) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT session_id, name, market, fleet_mw, status, created_at "
            "FROM dispatch_sessions WHERE api_key_hash=? ORDER BY created_at DESC",
            (api_key_hash,)
        ).fetchall()
        return [dict(r) for r in rows]


# ─── History Operations ───

def log_dispatch(api_key_hash: str, market: str, fleet_mw: float,
                 duration_hours: float, engine_type: str, total_fuel_kg: float,
                 fuel_savings_pct: float, dispatch_cost_usd: float,
                 savings_usd: float, solver_time_ms: float,
                 session_id: Optional[str] = None):
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO dispatch_history "
            "(session_id, api_key_hash, market, fleet_mw, duration_hours, engine_type, "
            "total_fuel_kg, fuel_savings_pct, dispatch_cost_usd, savings_usd, "
            "solver_time_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, api_key_hash, market, fleet_mw, duration_hours, engine_type,
             total_fuel_kg, fuel_savings_pct, dispatch_cost_usd, savings_usd,
             solver_time_ms, now)
        )


def get_dispatch_history(api_key_hash: str, limit: int = 50) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM dispatch_history WHERE api_key_hash=? "
            "ORDER BY created_at DESC LIMIT ?",
            (api_key_hash, limit)
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Usage Metrics ───

def log_usage(api_key_hash: str, endpoint: str, market: Optional[str],
              response_ms: float, status_code: int):
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO usage_metrics (api_key_hash, endpoint, market, "
            "response_ms, status_code, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (api_key_hash, endpoint, market, response_ms, status_code, now)
        )


def get_usage_summary(api_key_hash: str) -> dict:
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM usage_metrics WHERE api_key_hash=?",
            (api_key_hash,)
        ).fetchone()[0]

        today = datetime.now().strftime("%Y-%m-%d")
        today_count = conn.execute(
            "SELECT COUNT(*) FROM usage_metrics WHERE api_key_hash=? AND created_at LIKE ?",
            (api_key_hash, f"{today}%")
        ).fetchone()[0]

        return {"total_requests": total, "today_requests": today_count}


# Initialize on import
init_db()
