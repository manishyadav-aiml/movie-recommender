"""Tiny SQLite store for feedback messages. Every query is parameterised."""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect(path)) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
            name TEXT NOT NULL, email TEXT NOT NULL, message TEXT NOT NULL,
            utm_source TEXT, utm_medium TEXT, utm_campaign TEXT)""")
    try:
        os.chmod(path, 0o600)  # only the app user may read the database file
    except OSError:
        pass


def add_feedback(path: str, name: str, email: str, message: str, utm: dict) -> int:
    with closing(_connect(path)) as conn, conn:
        cur = conn.execute(
            "INSERT INTO feedback (created_at, name, email, message, utm_source, utm_medium, utm_campaign) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), name, email, message,
             utm.get("utm_source"), utm.get("utm_medium"), utm.get("utm_campaign")))
        return int(cur.lastrowid)


def list_feedback(path: str, limit: int = 200) -> list[sqlite3.Row]:
    with closing(_connect(path)) as conn:
        return conn.execute("SELECT * FROM feedback ORDER BY id DESC LIMIT ?", (limit,)).fetchall()


def delete_feedback(path: str, feedback_id: int) -> bool:
    with closing(_connect(path)) as conn, conn:
        return conn.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,)).rowcount > 0
