import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KANBAN_JWT_SECRET", "test-secret")
    app = create_app(db_path=str(tmp_path / "test.db"))
    with TestClient(app) as c:
        token = c.post(
            "/api/v1/auth/register",
            json={"email": "user@test.ru", "password": "password1"},
        ).json()["token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


@pytest.fixture
def board(client):
    return client.post("/api/v1/boards", json={"name": "Доска"}).json()


@pytest.fixture
def board_full(client, board):
    return client.get(f"/api/v1/boards/{board['id']}").json()


def make_task(client, board_id, column_id, title="Задача", **extra):
    r = client.post(
        "/api/v1/tasks",
        json={"board_id": board_id, "column_id": column_id, "title": title, **extra},
    )
    assert r.status_code == 201, r.text
    return r.json()
