from pydantic import BaseModel, Field

from app.schemas.columns import ColumnWithTasks


class BoardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    with_default_columns: bool = True


class BoardPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    archived: bool | None = None


class BoardOut(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    archived_at: str | None


class BoardListItem(BoardOut):
    task_count: int


class BoardFull(BoardOut):
    columns: list[ColumnWithTasks]
