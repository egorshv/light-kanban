"""Миграции: свежая БД собирается из schema.sql, старая — пошагово из MIGRATIONS."""

from app.repo import db

# Снимок схемы v1 (до auth) — чтобы проверить путь пошаговой миграции.
V1_DDL = """
CREATE TABLE boards (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 100),
    description TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    archived_at TEXT
);
CREATE TABLE columns (
    id        TEXT PRIMARY KEY,
    board_id  TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    name      TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 50),
    position  INTEGER NOT NULL,
    wip_limit INTEGER CHECK(wip_limit IS NULL OR wip_limit > 0),
    color     TEXT,
    is_final  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE tasks (
    id           TEXT PRIMARY KEY,
    board_id     TEXT NOT NULL REFERENCES boards(id)  ON DELETE CASCADE,
    column_id    TEXT NOT NULL REFERENCES columns(id),
    title        TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 200),
    description  TEXT DEFAULT '',
    position     INTEGER NOT NULL,
    priority     TEXT NOT NULL DEFAULT 'normal',
    due_date     TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE task_links (
    id             TEXT PRIMARY KEY,
    source_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    target_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    link_type      TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
"""


def columns_of(conn, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def test_fresh_db_bootstraps_to_current_version(conn):
    # conn-фикстура уже прогнала migrate по свежей :memory:
    (version,) = conn.execute("PRAGMA user_version").fetchone()
    assert version == db.SCHEMA_VERSION
    assert "owner_id" in columns_of(conn, "boards")
    assert {"id", "email", "password_hash", "google_sub"} <= columns_of(conn, "users")


def test_v1_db_migrates_stepwise():
    conn = db.connect(":memory:")
    conn.executescript(V1_DDL)
    conn.execute("PRAGMA user_version = 1")
    conn.execute(
        "INSERT INTO boards (id, name, created_at, updated_at) VALUES ('b1', 'Доска', 't', 't')"
    )
    conn.commit()

    db.migrate(conn)

    (version,) = conn.execute("PRAGMA user_version").fetchone()
    assert version == db.SCHEMA_VERSION
    assert "owner_id" in columns_of(conn, "boards")
    assert {"id", "email"} <= columns_of(conn, "users")
    # существующие данные не тронуты, owner_id пуст (доска-«сирота»)
    row = conn.execute("SELECT * FROM boards").fetchone()
    assert row["name"] == "Доска" and row["owner_id"] is None
    conn.close()
