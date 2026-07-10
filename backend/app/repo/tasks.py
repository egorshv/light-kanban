"""SQL для задач."""

import sqlite3


def insert(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        "INSERT INTO tasks (id, board_id, column_id, title, description, position,"
        " priority, due_date, created_at, updated_at, completed_at)"
        " VALUES (:id, :board_id, :column_id, :title, :description, :position,"
        " :priority, :due_date, :created_at, :updated_at, :completed_at)",
        row,
    )


def get(conn: sqlite3.Connection, task_id: str):
    return conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()


def list_by_column(conn: sqlite3.Connection, column_id: str):
    return conn.execute(
        "SELECT * FROM tasks WHERE column_id = ? ORDER BY position", (column_id,)
    ).fetchall()


def list_by_board_with_blocked(conn: sqlite3.Connection, board_id: str):
    """Задачи доски + флаг «заблокирована» (есть незавершённый блокер, US-D4)."""
    return conn.execute(
        """SELECT t.*, EXISTS(
               SELECT 1 FROM task_links l JOIN tasks blocker ON blocker.id = l.source_task_id
               WHERE l.target_task_id = t.id AND l.link_type = 'blocks'
                 AND blocker.completed_at IS NULL
           ) AS is_blocked
           FROM tasks t WHERE t.board_id = ? ORDER BY t.position""",
        (board_id,),
    ).fetchall()


def count_in_column(conn: sqlite3.Connection, column_id: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM tasks WHERE column_id = ?", (column_id,)).fetchone()[
        0
    ]


def update(conn: sqlite3.Connection, task_id: str, fields: dict) -> None:
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    conn.execute(f"UPDATE tasks SET {sets} WHERE id = :id", {**fields, "id": task_id})


def delete(conn: sqlite3.Connection, task_id: str) -> None:
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def renumber(conn: sqlite3.Connection, ordered_ids: list[str]) -> None:
    conn.executemany("UPDATE tasks SET position = ? WHERE id = ?", list(enumerate(ordered_ids)))


def search(conn: sqlite3.Connection, board_id: str, priority=None, due_before=None):
    sql = "SELECT * FROM tasks WHERE board_id = ?"
    params: list = [board_id]
    if priority:
        sql += " AND priority = ?"
        params.append(priority)
    if due_before:
        sql += " AND due_date IS NOT NULL AND due_date <= ?"
        params.append(due_before)
    sql += " ORDER BY position"
    return conn.execute(sql, params).fetchall()
