"""SQL для досок. Только SQL, никаких правил (ADR-006)."""

import sqlite3


def insert(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        "INSERT INTO boards (id, owner_id, name, description, created_at, updated_at, archived_at)"
        " VALUES (:id, :owner_id, :name, :description, :created_at, :updated_at, :archived_at)",
        row,
    )


def get(conn: sqlite3.Connection, board_id: str):
    return conn.execute("SELECT * FROM boards WHERE id = ?", (board_id,)).fetchone()


def list_all(conn: sqlite3.Connection, user_id: str, include_archived: bool):
    where = "" if include_archived else "AND b.archived_at IS NULL"
    return conn.execute(
        f"SELECT b.*, (SELECT COUNT(*) FROM tasks t WHERE t.board_id = b.id) AS task_count"
        f" FROM boards b WHERE b.owner_id = ? {where} ORDER BY b.created_at",
        (user_id,),
    ).fetchall()


def update(conn: sqlite3.Connection, board_id: str, fields: dict) -> None:
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    conn.execute(f"UPDATE boards SET {sets} WHERE id = :id", {**fields, "id": board_id})


def delete(conn: sqlite3.Connection, board_id: str) -> None:
    # Явный порядок: tasks ссылаются на columns без каскада, поэтому сначала задачи
    # (их удаление каскадно снимает связи, включая кросс-досочные), затем колонки и доска.
    conn.execute("DELETE FROM tasks WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM boards WHERE id = ?", (board_id,))


def task_count(conn: sqlite3.Connection, board_id: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM tasks WHERE board_id = ?", (board_id,)).fetchone()[0]
