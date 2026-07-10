import os

from fastapi import Header, HTTPException, Request

from app.repo import db


def get_conn(request: Request):
    conn = db.connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """ADR-009: KANBAN_TOKEN пуст ⇒ аутентификация выключена (локальный режим)."""
    token = os.environ.get("KANBAN_TOKEN", "")
    if token and authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Требуется корректный bearer-токен")
