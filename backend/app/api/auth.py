"""Роутер аутентификации: регистрация, вход, Google OAuth. Правила — в services/auth."""

import hmac
import os
import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.api.deps import current_user_id, get_conn
from app.errors import NotFound, Unauthorized
from app.schemas.auth import AuthOut, Credentials, RegisterIn, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _redirect_uri(request: Request) -> str:
    return os.environ.get("GOOGLE_REDIRECT_URI") or f"{request.base_url}api/v1/auth/google/callback"


@router.post("/register", response_model=AuthOut, status_code=201)
def register(body: RegisterIn, conn=Depends(get_conn)):
    user = auth_service.sign_up(conn, body.email, body.password, body.name)
    return {"token": auth_service.issue_jwt(user["id"]), "user": user}


@router.post("/login", response_model=AuthOut)
def login(body: Credentials, conn=Depends(get_conn)):
    user = auth_service.sign_in(conn, body.email, body.password)
    return {"token": auth_service.issue_jwt(user["id"]), "user": user}


@router.get("/me", response_model=UserOut)
def me(user_id: str = Depends(current_user_id), conn=Depends(get_conn)):
    return auth_service.get_user(conn, user_id)


@router.get("/google")
def google_redirect(request: Request):
    if not os.environ.get("GOOGLE_CLIENT_ID"):
        raise NotFound("Google-вход не настроен")
    state = secrets.token_urlsafe(16)
    resp = RedirectResponse(auth_service.google_auth_url(state, _redirect_uri(request)))
    resp.set_cookie("oauth_state", state, max_age=600, httponly=True, samesite="lax")
    return resp


@router.get("/google/callback")
def google_callback(code: str, state: str, request: Request, conn=Depends(get_conn)):
    if not hmac.compare_digest(state, request.cookies.get("oauth_state", "")):
        raise Unauthorized("Неверный параметр state")
    claims = auth_service.google_fetch_claims(code, _redirect_uri(request))
    user = auth_service.google_sign_in(conn, claims)
    # Токен во фрагменте URL: не попадает в логи сервера и прокси
    return RedirectResponse(f"/#/auth?token={auth_service.issue_jwt(user['id'])}")
