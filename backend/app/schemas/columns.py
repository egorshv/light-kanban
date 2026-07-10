from pydantic import BaseModel, Field

from app.schemas.tasks import TaskInBoard


class ColumnCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str | None = None
    wip_limit: int | None = Field(default=None, gt=0)
    is_final: bool = False


class ColumnPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = None
    wip_limit: int | None = Field(default=None, gt=0)
    is_final: bool | None = None


class ColumnMove(BaseModel):
    position: int = Field(ge=0)


class ColumnOut(BaseModel):
    id: str
    board_id: str
    name: str
    position: int
    wip_limit: int | None
    color: str | None
    is_final: bool


class ColumnWithTasks(ColumnOut):
    tasks: list[TaskInBoard]
