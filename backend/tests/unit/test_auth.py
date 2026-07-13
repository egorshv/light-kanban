"""Сервис auth: пароли, JWT, регистрация/вход, Google find-or-create."""

import pytest

from app.errors import Conflict, Unauthorized, ValidationError
from app.services import auth

CLAIMS = {"sub": "g-123", "email": "g@test.ru", "email_verified": True, "name": "Гоша"}


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("KANBAN_JWT_SECRET", "test-secret")


def test_password_hash_roundtrip():
    stored = auth.hash_password("пароль-123")
    assert auth.verify_password("пароль-123", stored)
    assert not auth.verify_password("другой", stored)
    # соль уникальна на каждый вызов
    assert stored != auth.hash_password("пароль-123")


def test_jwt_roundtrip():
    token = auth.issue_jwt("user-1")
    assert auth.verify_jwt(token) == "user-1"


def test_jwt_expired():
    token = auth.issue_jwt("user-1", ttl=-1)
    with pytest.raises(Unauthorized):
        auth.verify_jwt(token)


def test_jwt_tampered():
    header, payload, sig = auth.issue_jwt("user-1").split(".")
    for bad in (f"{header}.{payload}x.{sig}", f"{header}.{payload}", "мусор", ""):
        with pytest.raises(Unauthorized):
            auth.verify_jwt(bad)


def test_sign_up_validation(conn):
    with pytest.raises(ValidationError):
        auth.sign_up(conn, "не-email", "password1")
    with pytest.raises(ValidationError):
        auth.sign_up(conn, "a@b.ru", "коротк")


def test_sign_up_duplicate_email(conn):
    auth.sign_up(conn, "a@b.ru", "password1")
    with pytest.raises(Conflict):
        auth.sign_up(conn, "a@b.ru", "password2")
    # регистр не важен (COLLATE NOCASE)
    with pytest.raises(Conflict):
        auth.sign_up(conn, "A@B.RU", "password2")


def test_sign_in(conn):
    user = auth.sign_up(conn, "a@b.ru", "password1", name="Аня")
    assert auth.sign_in(conn, "a@b.ru", "password1") == user
    with pytest.raises(Unauthorized):
        auth.sign_in(conn, "a@b.ru", "неверный1")
    with pytest.raises(Unauthorized):
        auth.sign_in(conn, "нет@такого.ру", "password1")


def test_google_sign_in_creates_and_is_idempotent(conn):
    user = auth.google_sign_in(conn, CLAIMS)
    assert user["email"] == "g@test.ru" and user["name"] == "Гоша"
    assert auth.google_sign_in(conn, CLAIMS) == user
    # google-only пользователь не может войти по паролю
    with pytest.raises(Unauthorized):
        auth.sign_in(conn, "g@test.ru", "password1")


def test_google_sign_in_links_existing_email_user(conn):
    user = auth.sign_up(conn, "g@test.ru", "password1")
    assert auth.google_sign_in(conn, CLAIMS)["id"] == user["id"]
    # после привязки вход по sub находит того же пользователя
    assert auth.google_sign_in(conn, {**CLAIMS, "email": "другой@test.ru"})["id"] == user["id"]


def test_google_sign_in_requires_verified_profile(conn):
    for claims in ({}, {"sub": "x"}, {**CLAIMS, "email_verified": False}):
        with pytest.raises(Unauthorized):
            auth.google_sign_in(conn, claims)
