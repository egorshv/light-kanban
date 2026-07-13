"""Контракт /auth: регистрация, вход, /me, 401-формат, изоляция через API."""

from app.services import auth

CREDS = {"email": "user@test.ru", "password": "password1"}


def _error_code(r):
    return r.json()["error"]["code"]


def test_register_and_login(client):
    r = client.post("/api/v1/auth/register", json={"email": "new@test.ru", "password": "password1"})
    assert r.status_code == 201
    data = r.json()
    assert data["token"] and data["user"]["email"] == "new@test.ru"

    r = client.post("/api/v1/auth/login", json={"email": "new@test.ru", "password": "password1"})
    assert r.status_code == 200 and r.json()["user"]["id"] == data["user"]["id"]


def test_register_duplicate_email(client):
    r = client.post("/api/v1/auth/register", json=CREDS)  # уже создан фикстурой client
    assert r.status_code == 409
    assert _error_code(r) == "EMAIL_TAKEN"


def test_register_invalid_body(client):
    r = client.post("/api/v1/auth/register", json={"email": "не-email", "password": "password1"})
    assert r.status_code == 400
    r = client.post("/api/v1/auth/register", json={"email": "a@b.ru", "password": "коротк"})
    assert r.status_code == 400


def test_login_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={**CREDS, "password": "неверный1"})
    assert r.status_code == 401
    assert _error_code(r) == "UNAUTHORIZED"


def test_me(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 200 and r.json()["email"] == CREDS["email"]
    r = client.get("/api/v1/auth/me", headers={"Authorization": ""})
    assert r.status_code == 401 and _error_code(r) == "UNAUTHORIZED"


def test_protected_routes_require_token(client):
    for headers in (
        {"Authorization": ""},
        {"Authorization": "Bearer garbage.jwt.token"},
        {"Authorization": f"Bearer {auth.issue_jwt('user-x', ttl=-1)}"},
    ):
        r = client.get("/api/v1/boards", headers=headers)
        assert r.status_code == 401, headers
        assert _error_code(r) == "UNAUTHORIZED"
    # health доступен без токена (docker healthcheck)
    assert client.get("/api/v1/health", headers={"Authorization": ""}).status_code == 200


def test_isolation_between_users(client, board):
    # второй пользователь в том же приложении: свой токен, чужого не видно
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "b@test.ru", "password": "password2"},
        headers={"Authorization": ""},
    )
    headers_b = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.get("/api/v1/boards", headers=headers_b).json() == []
    assert client.get(f"/api/v1/boards/{board['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/boards/{board['id']}").status_code == 200
