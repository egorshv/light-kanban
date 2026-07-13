"""Соединение с SQLite и миграции (ADR-005: stdlib sqlite3, без ORM)."""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema.sql"
SCHEMA_VERSION = 2

# Пошаговые миграции существующих БД; свежая БД собирается сразу из schema.sql.
MIGRATIONS: dict[int, str] = {
    2: """
CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT,
    google_sub    TEXT UNIQUE,
    name          TEXT DEFAULT '',
    created_at    TEXT NOT NULL
);
ALTER TABLE boards ADD COLUMN owner_id TEXT REFERENCES users(id);
CREATE INDEX idx_boards_owner ON boards(owner_id);
""",
}


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """schema.sql (свежая БД) либо MIGRATIONS по шагам; применяется автоматически при старте."""
    (version,) = conn.execute("PRAGMA user_version").fetchone()
    if version == 0:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    else:
        for v in range(version + 1, SCHEMA_VERSION + 1):
            conn.executescript(MIGRATIONS[v])
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
