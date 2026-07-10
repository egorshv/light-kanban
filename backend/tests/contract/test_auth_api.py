from fastapi.testclient import TestClient

from app.main import create_app


def test_auth_enforced_when_token_set(tmp_path, monkeypatch):
    monkeypatch.setenv("KANBAN_TOKEN", "secret")
    app = create_app(db_path=str(tmp_path / "auth.db"))
    with TestClient(app) as client:
        r = client.get("/api/v1/boards")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHORIZED"

        r = client.get("/api/v1/boards", headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401

        r = client.get("/api/v1/boards", headers={"Authorization": "Bearer secret"})
        assert r.status_code == 200

        # health доступен без токена (docker healthcheck)
        assert client.get("/api/v1/health").status_code == 200


def test_auth_disabled_without_token(client):
    assert client.get("/api/v1/boards").status_code == 200
