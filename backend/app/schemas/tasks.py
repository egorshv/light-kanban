from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["low", "normal", "high", "urgent"]
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class TaskCreate(BaseModel):
    board_id: str
    column_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: Priority = "normal"
    due_date: str | None = Field(default=None, pattern=DATE_PATTERN)


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: Priority | None = None
    due_date: str | None = Field(default=None, pattern=DATE_PATTERN)


class TaskMove(BaseModel):
    column_id: str
    position: int = Field(ge=0)


class TaskOut(BaseModel):
    id: str
    board_id: str
    column_id: str
    title: str
    description: str
    position: int
    priority: Priority
    due_date: str | None
    created_at: str
    updated_at: str
    completed_at: str | None


class TaskInBoard(TaskOut):
    is_blocked: bool


class WipWarning(BaseModel):
    column_id: str
    column_name: str
    wip_limit: int
    task_count: int


class TaskWithWarning(TaskOut):
    wip_warning: WipWarning | None
