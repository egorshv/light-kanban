"""Аутентификация: пароли (scrypt), JWT HS256 на stdlib, Google OAuth через httpx.

JWT без PyJWT сознательно: проверяем только собственные токены с фиксированным
алгоритмом, поле alg из заголовка никогда не читается — alg-confusion невозможен.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from urllib.parse import urlencode

import httpx

from app.errors import Conflict, NotFound, Unauthorized, ValidationError
from app.repo import users as users_repo
from app.services.common import check_len, log_event, new_id, now_iso

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_JWT_HEADER = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _secret() -> bytes:
    return os.environ["KANBAN_JWT_SECRET"].encode()


def _ttl() -> int:
    return int(os.environ.get("KANBAN_JWT_TTL", "86400"))


# --- пароли -----------------------------------------------------------------


def _scrypt(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"{salt.hex()}${_scrypt(password, salt).hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, key_hex = stored.split("$")
    return hmac.compare_digest(_scrypt(password, bytes.fromhex(salt_hex)), bytes.fromhex(key_hex))


# --- JWT --------------------------------------------------------------------


def _b64(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _sign(msg: bytes) -> bytes:
    return _b64(hmac.new(_secret(), msg, hashlib.sha256).digest())


def issue_jwt(user_id: str, ttl: int | None = None) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + (ttl if ttl is not None else _ttl())}
    msg = _JWT_HEADER + b"." + _b64(json.dumps(payload).encode())
    return (msg + b"." + _sign(msg)).decode()


def verify_jwt(token: str) -> str:
    """Проверяет подпись и срок, возвращает sub. Любая ошибка ⇒ Unauthorized."""
    try:
        header, payload_b64, signature = token.encode().split(b".")
        if not hmac.compare_digest(_sign(header + b"." + payload_b64), signature):
            raise Unauthorized()
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + b"=="))
        if not isinstance(payload["sub"], str) or payload["exp"] < time.time():
            raise Unauthorized()
        return payload["sub"]
    except (ValueError, KeyError, TypeError):
        raise Unauthorized() from None


# --- регистрация и вход -----------------------------------------------------


def _public(row) -> dict:
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def sign_up(conn, email: str, password: str, name: str = "") -> dict:
    if not isinstance(email, str) or not EMAIL_RE.fullmatch(email):
        raise ValidationError("Поле 'email' должно быть корректным email-адресом")
    check_len(password, 8, 128, "password")
    if users_repo.get_by_email(conn, email) is not None:
        raise Conflict("Email уже зарегистрирован", code="EMAIL_TAKEN")
    user = {
        "id": new_id(),
        "email": email,
        "password_hash": hash_password(password),
        "google_sub": None,
        "name": name or "",
        "created_at": now_iso(),
    }
    with conn:
        users_repo.insert(conn, user)
    log_event("user.registered", user_id=user["id"])
    return _public(user)


def sign_in(conn, email: str, password: str) -> dict:
    row = users_repo.get_by_email(conn, email) if isinstance(email, str) else None
    if (
        row is None
        or row["password_hash"] is None
        or not verify_password(password, row["password_hash"])
    ):
        raise Unauthorized("Неверный email или пароль")
    return _public(row)


def get_user(conn, user_id: str) -> dict:
    row = users_repo.get(conn, user_id)
    if row is None:
        raise NotFound("Пользователь не найден")
    return _public(row)


# --- Google OAuth (authorization code flow) ----------------------------------


def google_auth_url(state: str, redirect_uri: str) -> str:
    params = {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def google_fetch_claims(code: str, redirect_uri: str) -> dict:
    """Обмен кода на access_token и запрос userinfo. Ошибки Google ⇒ Unauthorized."""
    try:
        token_resp = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        info_resp = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_resp.json()['access_token']}"},
            timeout=10,
        )
        info_resp.raise_for_status()
        return info_resp.json()
    except (httpx.HTTPError, KeyError):
        raise Unauthorized("Не удалось выполнить вход через Google") from None


def google_sign_in(conn, claims: dict) -> dict:
    """Find-or-create: по google_sub → по подтверждённому email (привязка) → создание."""
    sub, email = claims.get("sub"), claims.get("email")
    if not sub or not email or not claims.get("email_verified"):
        raise Unauthorized("Google не вернул подтверждённый профиль пользователя")
    row = users_repo.get_by_google_sub(conn, sub)
    if row is not None:
        return _public(row)
    row = users_repo.get_by_email(conn, email)
    if row is not None:
        with conn:
            users_repo.update(conn, row["id"], {"google_sub": sub})
        return _public(row)
    user = {
        "id": new_id(),
        "email": email,
        "password_hash": None,
        "google_sub": sub,
        "name": claims.get("name") or "",
        "created_at": now_iso(),
    }
    with conn:
        users_repo.insert(conn, user)
    log_event("user.registered", user_id=user["id"], via="google")
    return _public(user)
