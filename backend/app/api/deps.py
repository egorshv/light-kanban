from fastapi import Header, Request

from app.errors import Unauthorized
from app.repo import db
from app.services import auth as auth_service


def get_conn(request: Request):
    conn = db.connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


def current_user_id(authorization: str | None = Header(default=None)) -> str:
    """JWT из Authorization: Bearer → id пользователя. Иначе 401."""
    if not authorization or not authorization.startswith("Bearer "):
        raise Unauthorized()
    return auth_service.verify_jwt(authorization[7:])
