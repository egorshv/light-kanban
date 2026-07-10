from typing import Literal

from pydantic import BaseModel

from app.schemas.tasks import TaskOut

LinkType = Literal["blocks", "subtask_of", "relates_to", "duplicates"]


class LinkCreate(BaseModel):
    source_task_id: str
    target_task_id: str
    link_type: LinkType


class LinkOut(BaseModel):
    id: str
    source_task_id: str
    target_task_id: str
    link_type: LinkType
    created_at: str


class LinkedTaskRef(BaseModel):
    id: str
    title: str
    board_id: str
    completed_at: str | None


class TaskLinkOut(BaseModel):
    id: str
    link_type: LinkType
    direction: Literal["out", "in"]
    created_at: str
    other_task: LinkedTaskRef


class TaskWithLinks(TaskOut):
    links: list[TaskLinkOut]
