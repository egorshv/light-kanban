"""SQL для связей задач."""

import sqlite3


def insert(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        "INSERT INTO task_links (id, source_task_id, target_task_id, link_type, created_at)"
        " VALUES (:id, :source_task_id, :target_task_id, :link_type, :created_at)",
        row,
    )


def get(conn: sqlite3.Connection, link_id: str):
    return conn.execute("SELECT * FROM task_links WHERE id = ?", (link_id,)).fetchone()


def delete(conn: sqlite3.Connection, link_id: str) -> None:
    conn.execute("DELETE FROM task_links WHERE id = ?", (link_id,))


def exists(
    conn: sqlite3.Connection, source_task_id: str, target_task_id: str, link_type: str
) -> bool:
    row = conn.execute(
        "SELECT 1 FROM task_links"
        " WHERE source_task_id = ? AND target_task_id = ? AND link_type = ?",
        (source_task_id, target_task_id, link_type),
    ).fetchone()
    return row is not None


def source_has_parent(conn: sqlite3.Connection, task_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM task_links WHERE source_task_id = ? AND link_type = 'subtask_of'",
        (task_id,),
    ).fetchone()
    return row is not None


def target_ids_from(conn: sqlite3.Connection, task_id: str, link_type: str) -> list[str]:
    rows = conn.execute(
        "SELECT target_task_id FROM task_links WHERE source_task_id = ? AND link_type = ?",
        (task_id, link_type),
    ).fetchall()
    return [r[0] for r in rows]


def list_for_task(conn: sqlite3.Connection, task_id: str):
    return conn.execute(
        """SELECT l.*,
                  s.title AS source_title, s.board_id AS source_board_id,
                  s.completed_at AS source_completed_at,
                  tt.title AS target_title, tt.board_id AS target_board_id,
                  tt.completed_at AS target_completed_at
           FROM task_links l
           JOIN tasks s  ON s.id  = l.source_task_id
           JOIN tasks tt ON tt.id = l.target_task_id
           WHERE l.source_task_id = ? OR l.target_task_id = ?
           ORDER BY l.created_at""",
        (task_id, task_id),
    ).fetchall()
