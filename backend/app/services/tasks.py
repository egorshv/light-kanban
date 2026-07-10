"""Доменные операции над задачами: позиции, WIP, is_final → completed_at."""

from datetime import date

from app.errors import Conflict, NotFound, ValidationError
from app.repo import boards as boards_repo
from app.repo import columns as columns_repo
from app.repo import links as links_repo
from app.repo import tasks as tasks_repo
from app.services.common import PRIORITIES, check_enum, check_len, log_event, new_id, now_iso


def get_task(conn, task_id: str) -> dict:
    row = tasks_repo.get(conn, task_id)
    if row is None:
        raise NotFound("Задача не найдена")
    return dict(row)


def _get_column(conn, column_id: str) -> dict:
    row = columns_repo.get(conn, column_id)
    if row is None:
        raise NotFound("Колонка не найдена")
    return dict(row)


def _check_due_date(value):
    if value is None:
        return None
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError("Поле 'due_date' должно быть датой в формате YYYY-MM-DD")
    return value


def completed_at_on_enter(column: dict, current_completed_at, now: str):
    """Решение №3 плана: вход в финальную колонку проставляет completed_at, выход сбрасывает."""
    if column["is_final"]:
        return current_completed_at or now
    return None


def _wip_warning(conn, column: dict) -> dict | None:
    """WIP-лимит мягкий: предупреждение, не блокировка (§2). Вызывается после вставки."""
    if column["wip_limit"] is None:
        return None
    count = tasks_repo.count_in_column(conn, column["id"])
    if count > column["wip_limit"]:
        return {
            "column_id": column["id"],
            "column_name": column["name"],
            "wip_limit": column["wip_limit"],
            "task_count": count,
        }
    return None


def create_task(conn, board_id, column_id, title, description="", priority="normal", due_date=None):
    if boards_repo.get(conn, board_id) is None:
        raise NotFound("Доска не найдена")
    column = _get_column(conn, column_id)
    if column["board_id"] != board_id:
        raise Conflict("Колонка не принадлежит указанной доске")
    check_len(title, 1, 200, "title")
    check_enum(priority, PRIORITIES, "priority")
    _check_due_date(due_date)
    now = now_iso()
    task = {
        "id": new_id(),
        "board_id": board_id,
        "column_id": column_id,
        "title": title,
        "description": description or "",
        "position": tasks_repo.count_in_column(conn, column_id),
        "priority": priority,
        "due_date": due_date,
        "created_at": now,
        "updated_at": now,
        "completed_at": now if column["is_final"] else None,
    }
    with conn:
        tasks_repo.insert(conn, task)
        warning = _wip_warning(conn, column)
    log_event("task.created", task_id=task["id"], board_id=board_id, column_id=column_id)
    return task, warning


def update_task(conn, task_id: str, fields: dict) -> dict:
    get_task(conn, task_id)
    updates = {}
    if "title" in fields:
        updates["title"] = check_len(fields["title"], 1, 200, "title")
    if "description" in fields:
        updates["description"] = fields["description"] or ""
    if "priority" in fields:
        updates["priority"] = check_enum(fields["priority"], PRIORITIES, "priority")
    if "due_date" in fields:
        updates["due_date"] = _check_due_date(fields["due_date"])
    if updates:
        updates["updated_at"] = now_iso()
        with conn:
            tasks_repo.update(conn, task_id, updates)
        log_event("task.updated", task_id=task_id, fields=sorted(updates))
    return get_task(conn, task_id)


def move_task(conn, task_id: str, column_id: str, position: int):
    """Атомарное перемещение с полным пересчётом позиций затронутых колонок (§5)."""
    task = get_task(conn, task_id)
    target = _get_column(conn, column_id)
    if target["board_id"] != task["board_id"]:
        raise Conflict("Нельзя переместить задачу на другую доску")
    now = now_iso()
    same_column = column_id == task["column_id"]
    with conn:
        if same_column:
            ids = [r["id"] for r in tasks_repo.list_by_column(conn, column_id)]
            ids.remove(task_id)
            ids.insert(max(0, min(position, len(ids))), task_id)
            tasks_repo.renumber(conn, ids)
        else:
            source_ids = [
                r["id"]
                for r in tasks_repo.list_by_column(conn, task["column_id"])
                if r["id"] != task_id
            ]
            tasks_repo.renumber(conn, source_ids)
            target_ids = [r["id"] for r in tasks_repo.list_by_column(conn, column_id)]
            target_ids.insert(max(0, min(position, len(target_ids))), task_id)
            tasks_repo.update(conn, task_id, {"column_id": column_id})
            tasks_repo.renumber(conn, target_ids)
        tasks_repo.update(
            conn,
            task_id,
            {
                "completed_at": completed_at_on_enter(target, task["completed_at"], now),
                "updated_at": now,
            },
        )
        warning = None if same_column else _wip_warning(conn, target)
    log_event(
        "task.moved",
        task_id=task_id,
        from_column=task["column_id"],
        to_column=column_id,
        position=position,
    )
    return get_task(conn, task_id), warning


def delete_task(conn, task_id: str) -> None:
    task = get_task(conn, task_id)
    with conn:
        tasks_repo.delete(conn, task_id)  # связи удаляются каскадом (FK)
        tasks_repo.renumber(
            conn, [r["id"] for r in tasks_repo.list_by_column(conn, task["column_id"])]
        )
    log_event("task.deleted", task_id=task_id, board_id=task["board_id"])


def get_task_with_links(conn, task_id: str) -> dict:
    task = get_task(conn, task_id)
    links = []
    for row in links_repo.list_for_task(conn, task_id):
        out = row["source_task_id"] == task_id
        links.append(
            {
                "id": row["id"],
                "link_type": row["link_type"],
                "direction": "out" if out else "in",
                "created_at": row["created_at"],
                "other_task": {
                    "id": row["target_task_id"] if out else row["source_task_id"],
                    "title": row["target_title"] if out else row["source_title"],
                    "board_id": row["target_board_id"] if out else row["source_board_id"],
                    "completed_at": row["target_completed_at"]
                    if out
                    else row["source_completed_at"],
                },
            }
        )
    task["links"] = links
    return task


def search_tasks(conn, board_id: str, q=None, priority=None, due_before=None) -> list[dict]:
    if boards_repo.get(conn, board_id) is None:
        raise NotFound("Доска не найдена")
    if priority:
        check_enum(priority, PRIORITIES, "priority")
    if due_before:
        _check_due_date(due_before)
    rows = [dict(r) for r in tasks_repo.search(conn, board_id, priority, due_before)]
    if q:
        # ponytail: подстрочный поиск в Python — LIKE/lower() в SQLite не знают кириллицу;
        # FTS5 — когда объёмы перерастут персональные
        needle = q.lower()
        rows = [
            t
            for t in rows
            if needle in t["title"].lower() or needle in (t["description"] or "").lower()
        ]
    return rows
