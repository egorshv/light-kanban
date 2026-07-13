from fastapi import APIRouter, Depends

from app.api.deps import current_user_id, get_conn
from app.schemas.links import TaskWithLinks
from app.schemas.tasks import TaskCreate, TaskMove, TaskOut, TaskPatch, TaskWithWarning
from app.services import tasks as tasks_service

router = APIRouter(tags=["tasks"])


@router.post("/tasks", response_model=TaskWithWarning, status_code=201)
def create_task(body: TaskCreate, user_id: str = Depends(current_user_id), conn=Depends(get_conn)):
    task, warning = tasks_service.create_task(
        conn,
        user_id,
        body.board_id,
        body.column_id,
        body.title,
        body.description,
        body.priority,
        body.due_date,
    )
    return {**task, "wip_warning": warning}


@router.get("/tasks/{task_id}", response_model=TaskWithLinks)
def get_task(task_id: str, user_id: str = Depends(current_user_id), conn=Depends(get_conn)):
    return tasks_service.get_task_with_links(conn, user_id, task_id)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    body: TaskPatch,
    user_id: str = Depends(current_user_id),
    conn=Depends(get_conn),
):
    return tasks_service.update_task(conn, user_id, task_id, body.model_dump(exclude_unset=True))


@router.post("/tasks/{task_id}/move", response_model=TaskWithWarning)
def move_task(
    task_id: str,
    body: TaskMove,
    user_id: str = Depends(current_user_id),
    conn=Depends(get_conn),
):
    task, warning = tasks_service.move_task(conn, user_id, task_id, body.column_id, body.position)
    return {**task, "wip_warning": warning}


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, user_id: str = Depends(current_user_id), conn=Depends(get_conn)):
    tasks_service.delete_task(conn, user_id, task_id)


@router.get("/boards/{board_id}/tasks", response_model=list[TaskOut])
def search_tasks(
    board_id: str,
    q: str | None = None,
    priority: str | None = None,
    due_before: str | None = None,
    user_id: str = Depends(current_user_id),
    conn=Depends(get_conn),
):
    return tasks_service.search_tasks(conn, user_id, board_id, q, priority, due_before)
