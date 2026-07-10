import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("KANBAN_TOKEN", raising=False)
    app = create_app(db_path=str(tmp_path / "test.db"))
    with TestClient(app) as c:
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
