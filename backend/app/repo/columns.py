"""SQL для колонок."""

import sqlite3


def insert(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        "INSERT INTO columns (id, board_id, name, position, wip_limit, color, is_final)"
        " VALUES (:id, :board_id, :name, :position, :wip_limit, :color, :is_final)",
        row,
    )


def get(conn: sqlite3.Connection, column_id: str):
    return conn.execute("SELECT * FROM columns WHERE id = ?", (column_id,)).fetchone()


def list_by_board(conn: sqlite3.Connection, board_id: str):
    return conn.execute(
        "SELECT * FROM columns WHERE board_id = ? ORDER BY position", (board_id,)
    ).fetchall()


def count_by_board(conn: sqlite3.Connection, board_id: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM columns WHERE board_id = ?", (board_id,)).fetchone()[
        0
    ]


def update(conn: sqlite3.Connection, column_id: str, fields: dict) -> None:
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    conn.execute(f"UPDATE columns SET {sets} WHERE id = :id", {**fields, "id": column_id})


def delete(conn: sqlite3.Connection, column_id: str) -> None:
    conn.execute("DELETE FROM columns WHERE id = ?", (column_id,))


def renumber(conn: sqlite3.Connection, ordered_ids: list[str]) -> None:
    conn.executemany("UPDATE columns SET position = ? WHERE id = ?", list(enumerate(ordered_ids)))
