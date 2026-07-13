"""Доменные операции над связями: self-link, дубликаты, один родитель, циклы (DFS)."""

from app.errors import DomainRuleViolation, NotFound
from app.repo import links as links_repo
from app.repo import tasks as tasks_repo
from app.services import boards as boards_service
from app.services.common import LINK_TYPES, check_enum, log_event, new_id, now_iso

CYCLE_CHECKED = ("blocks", "subtask_of")


def _get_task(conn, user_id: str, task_id: str, role: str) -> dict:
    row = tasks_repo.get(conn, task_id)
    if row is None:
        raise NotFound(f"Задача ({role}) не найдена")
    boards_service.get_board(conn, user_id, row["board_id"])  # обе стороны — только свои доски
    return dict(row)


def _find_path(conn, start: str, goal: str, link_type: str) -> list[str] | None:
    """DFS по рёбрам source→target данного типа; путь start..goal или None."""
    stack = [(start, [start])]
    seen: set[str] = set()
    while stack:
        node, path = stack.pop()
        if node == goal:
            return path
        if node in seen:
            continue
        seen.add(node)
        for nxt in links_repo.target_ids_from(conn, node, link_type):
            stack.append((nxt, path + [nxt]))
    return None


def create_link(
    conn, user_id: str, source_task_id: str, target_task_id: str, link_type: str
) -> dict:
    check_enum(link_type, LINK_TYPES, "link_type")
    source = _get_task(conn, user_id, source_task_id, "источник")
    _get_task(conn, user_id, target_task_id, "цель")
    if source_task_id == target_task_id:
        raise DomainRuleViolation("SELF_LINK", "Нельзя связать задачу с самой собой")
    if links_repo.exists(conn, source_task_id, target_task_id, link_type):
        raise DomainRuleViolation("DUPLICATE_LINK", "Такая связь уже существует")
    if link_type == "relates_to" and links_repo.exists(
        conn, target_task_id, source_task_id, link_type
    ):
        # relates_to симметрична (§2) — обратная пара это та же самая связь
        raise DomainRuleViolation("DUPLICATE_LINK", "Такая связь уже существует")
    if link_type == "subtask_of" and links_repo.source_has_parent(conn, source_task_id):
        raise DomainRuleViolation("PARENT_EXISTS", "У задачи уже есть родительская задача")
    if link_type in CYCLE_CHECKED:
        path = _find_path(conn, target_task_id, source_task_id, link_type)
        if path is not None:
            titles = [source["title"]] + [
                _get_task(conn, user_id, tid, "цикл")["title"] for tid in path
            ]
            raise DomainRuleViolation("LINK_CYCLE", "Связь создаёт цикл: " + " → ".join(titles))
    link = {
        "id": new_id(),
        "source_task_id": source_task_id,
        "target_task_id": target_task_id,
        "link_type": link_type,
        "created_at": now_iso(),
    }
    with conn:
        links_repo.insert(conn, link)
    log_event("link.created", link_id=link["id"], link_type=link_type)
    return link


def delete_link(conn, user_id: str, link_id: str) -> None:
    link = links_repo.get(conn, link_id)
    if link is None:
        raise NotFound("Связь не найдена")
    # связи существуют только между досками одного владельца — проверки источника достаточно
    _get_task(conn, user_id, link["source_task_id"], "источник")
    with conn:
        links_repo.delete(conn, link_id)
    log_event("link.deleted", link_id=link_id)
