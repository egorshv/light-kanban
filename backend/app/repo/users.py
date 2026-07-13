"""SQL для пользователей. Только SQL, никаких правил (ADR-006)."""

import sqlite3


def insert(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        "INSERT INTO users (id, email, password_hash, google_sub, name, created_at)"
        " VALUES (:id, :email, :password_hash, :google_sub, :name, :created_at)",
        row,
    )


def get(conn: sqlite3.Connection, user_id: str):
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_by_email(conn: sqlite3.Connection, email: str):
    # COLLATE NOCASE на колонке делает сравнение регистронезависимым
    return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_by_google_sub(conn: sqlite3.Connection, sub: str):
    return conn.execute("SELECT * FROM users WHERE google_sub = ?", (sub,)).fetchone()


def update(conn: sqlite3.Connection, user_id: str, fields: dict) -> None:
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    conn.execute(f"UPDATE users SET {sets} WHERE id = :id", {**fields, "id": user_id})
