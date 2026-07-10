"""Доменные операции над досками."""

from app.errors import NotFound
from app.repo import boards as boards_repo
from app.repo import columns as columns_repo
from app.repo import tasks as tasks_repo
from app.services.common import check_len, log_event, new_id, now_iso

# US-A1 AC2: колонки по умолчанию; «Готово» — финальная (решение №3 плана)
DEFAULT_COLUMNS = (("Backlog", 0), ("В работе", 0), ("Готово", 1))


def get_board(conn, board_id: str) -> dict:
    row = boards_repo.get(conn, board_id)
    if row is None:
        raise NotFound("Доска не найдена")
    return dict(row)


def create_board(conn, name: str, description: str = "", with_default_columns: bool = True) -> dict:
    check_len(name, 1, 100, "name")
    now = now_iso()
    board = {
        "id": new_id(),
        "name": name,
        "description": description or "",
        "created_at": now,
        "updated_at": now,
        "archived_at": None,
    }
    with conn:
        boards_repo.insert(conn, board)
        if with_default_columns:
            for position, (col_name, is_final) in enumerate(DEFAULT_COLUMNS):
                columns_repo.insert(
                    conn,
                    {
                        "id": new_id(),
                        "board_id": board["id"],
                        "name": col_name,
                        "position": position,
                        "wip_limit": None,
                        "color": None,
                        "is_final": is_final,
                    },
                )
    log_event("board.created", board_id=board["id"], name=name)
    return board


def get_board_full(conn, board_id: str) -> dict:
    """Доска целиком (колонки + задачи) — основной запрос UI, одна выборка на таблицу."""
    board = get_board(conn, board_id)
    columns = [dict(c) for c in columns_repo.list_by_board(conn, board_id)]
    by_column = {c["id"]: c for c in columns}
    for c in columns:
        c["tasks"] = []
    for t in tasks_repo.list_by_board_with_blocked(conn, board_id):
        by_column[t["column_id"]]["tasks"].append(dict(t))
    board["columns"] = columns
    return board


def list_boards(conn, include_archived: bool = False) -> list[dict]:
    return [dict(r) for r in boards_repo.list_all(conn, include_archived)]


def update_board(conn, board_id: str, fields: dict) -> dict:
    get_board(conn, board_id)
    updates = {}
    if "name" in fields:
        updates["name"] = check_len(fields["name"], 1, 100, "name")
    if "description" in fields:
        updates["description"] = fields["description"] or ""
    if "archived" in fields:
        updates["archived_at"] = now_iso() if fields["archived"] else None
    if updates:
        updates["updated_at"] = now_iso()
        with conn:
            boards_repo.update(conn, board_id, updates)
        log_event("board.updated", board_id=board_id, fields=sorted(updates))
    return get_board(conn, board_id)


def delete_board(conn, board_id: str) -> None:
    get_board(conn, board_id)
    count = boards_repo.task_count(conn, board_id)
    with conn:
        boards_repo.delete(conn, board_id)
    log_event("board.deleted", board_id=board_id, task_count=count)
