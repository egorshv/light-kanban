"""Общие помощники сервисного слоя: id, время, валидация, доменные события."""

import logging
import uuid
from datetime import datetime, timezone

from app.errors import ValidationError

# ADR-010: журнал доменных событий — задел под календарную синхронизацию этапа 3
events = logging.getLogger("kanban.events")

PRIORITIES = ("low", "normal", "high", "urgent")
LINK_TYPES = ("blocks", "subtask_of", "relates_to", "duplicates")


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_len(value, lo: int, hi: int, field: str) -> str:
    if not isinstance(value, str) or not (lo <= len(value) <= hi):
        raise ValidationError(f"Поле '{field}' должно быть строкой длиной {lo}–{hi} символов")
    return value


def check_enum(value, allowed: tuple, field: str) -> str:
    if value not in allowed:
        raise ValidationError(f"Поле '{field}' должно быть одним из: {', '.join(allowed)}")
    return value


def log_event(event: str, **data) -> None:
    events.info(event, extra={"data": data})
