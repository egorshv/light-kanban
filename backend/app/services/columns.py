"""Доменные операции над колонками: позиции, «последняя колонка», два сценария удаления."""

from app.errors import Conflict, NotFound, ValidationError
from app.repo import columns as columns_repo
from app.repo import tasks as tasks_repo
from app.services import boards as boards_service
from app.services.common import check_len, log_event, new_id, now_iso
from app.services.tasks import completed_at_on_enter


def _check_wip(wip_limit):
    if wip_limit is not None and (not isinstance(wip_limit, int) or wip_limit <= 0):
        raise ValidationError("Поле 'wip_limit' должно быть положительным числом")
    return wip_limit


def get_column(conn, column_id: str) -> dict:
    row = columns_repo.get(conn, column_id)
    if row is None:
        raise NotFound("Колонка не найдена")
    return dict(row)


def create_column(conn, board_id, name, color=None, wip_limit=None, is_final=False) -> dict:
    boards_service.get_board(conn, board_id)
    check_len(name, 1, 50, "name")
    _check_wip(wip_limit)
    column = {
        "id": new_id(),
        "board_id": board_id,
        "name": name,
        "position": columns_repo.count_by_board(conn, board_id),  # US-B1 AC2: в конец
        "wip_limit": wip_limit,
        "color": color,
        "is_final": 1 if is_final else 0,
    }
    with conn:
        columns_repo.insert(conn, column)
    log_event("column.created", column_id=column["id"], board_id=board_id)
    return get_column(conn, column["id"])


def update_column(conn, column_id: str, fields: dict) -> dict:
    get_column(conn, column_id)
    updates = {}
    if "name" in fields:
        updates["name"] = check_len(fields["name"], 1, 50, "name")
    if "color" in fields:
        updates["color"] = fields["color"]
    if "wip_limit" in fields:
        updates["wip_limit"] = _check_wip(fields["wip_limit"])
    if "is_final" in fields:
        updates["is_final"] = 1 if fields["is_final"] else 0
    if updates:
        with conn:
            columns_repo.update(conn, column_id, updates)
        log_event("column.updated", column_id=column_id, fields=sorted(updates))
    return get_column(conn, column_id)


def move_column(conn, column_id: str, position: int) -> dict:
    column = get_column(conn, column_id)
    with conn:
        ids = [r["id"] for r in columns_repo.list_by_board(conn, column["board_id"])]
        ids.remove(column_id)
        ids.insert(max(0, min(position, len(ids))), column_id)
        columns_repo.renumber(conn, ids)  # полный пересчёт в транзакции (§5)
    log_event("column.moved", column_id=column_id, position=position)
    return get_column(conn, column_id)


def delete_column(conn, column_id: str, move_tasks_to: str | None = None) -> None:
    """US-B4: два явных сценария — перенос задач в целевую колонку либо 409."""
    column = get_column(conn, column_id)
    if columns_repo.count_by_board(conn, column["board_id"]) == 1:
        raise Conflict("Нельзя удалить последнюю колонку доски", code="LAST_COLUMN")
    tasks = tasks_repo.list_by_column(conn, column_id)
    target = None
    if tasks:
        if move_tasks_to is None:
            raise Conflict(
                "В колонке есть задачи: укажите move_tasks_to или удалите задачи",
                code="COLUMN_NOT_EMPTY",
            )
        target = get_column(conn, move_tasks_to)
        if target["id"] == column_id:
            raise Conflict("Целевая колонка совпадает с удаляемой")
        if target["board_id"] != column["board_id"]:
            raise Conflict("Целевая колонка находится на другой доске")
    with conn:
        if target is not None:
            now = now_iso()
            offset = tasks_repo.count_in_column(conn, target["id"])
            for i, task in enumerate(tasks):  # в конец целевой, с сохранением порядка
                tasks_repo.update(
                    conn,
                    task["id"],
                    {
                        "column_id": target["id"],
                        "position": offset + i,
                        "completed_at": completed_at_on_enter(target, task["completed_at"], now),
                        "updated_at": now,
                    },
                )
        columns_repo.delete(conn, column_id)
        columns_repo.renumber(
            conn, [r["id"] for r in columns_repo.list_by_board(conn, column["board_id"])]
        )
    log_event("column.deleted", column_id=column_id, moved_tasks=len(tasks))
