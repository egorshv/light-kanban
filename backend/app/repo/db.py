"""Соединение с SQLite и миграции (ADR-005: stdlib sqlite3, без ORM)."""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema.sql"
SCHEMA_VERSION = 1


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """schema.sql + PRAGMA user_version; применяется автоматически при старте."""
    (version,) = conn.execute("PRAGMA user_version").fetchone()
    if version < SCHEMA_VERSION:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
