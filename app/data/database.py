"""SQLite persistence for run history (stdlib only — no server)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import PROJECT_ROOT, settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    session_id    TEXT,
    timestamp     TEXT,
    environment   TEXT,
    scenario_id   TEXT,
    reasoning_mode TEXT,
    tools_used    TEXT,
    providers     TEXT,
    execution_ms  REAL,
    success       INTEGER,
    degraded      INTEGER,
    errors        TEXT,
    trace         TEXT
);
"""


def _db_path() -> Path:
    path = Path(settings.db_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def save_run(record: Dict[str, Any]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO runs
            (run_id, session_id, timestamp, environment, scenario_id, reasoning_mode,
             tools_used, providers, execution_ms, success, degraded, errors, trace)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["run_id"],
                record.get("session_id"),
                record.get("timestamp"),
                record.get("environment"),
                record.get("scenario_id"),
                record.get("reasoning_mode"),
                json.dumps(record.get("tools_used", [])),
                json.dumps(record.get("providers", {})),
                float(record.get("execution_ms", 0.0)),
                1 if record.get("success") else 0,
                1 if record.get("degraded") else 0,
                json.dumps(record.get("errors", [])),
                json.dumps(record.get("trace", [])),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def recent_runs(limit: int = 25) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    finally:
        conn.close()
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        for key in ("tools_used", "providers", "errors", "trace"):
            try:
                item[key] = json.loads(item[key]) if item[key] else None
            except (TypeError, json.JSONDecodeError):
                pass
        out.append(item)
    return out
