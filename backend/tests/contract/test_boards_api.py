from tests.contract.conftest import make_task


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_board(client):
    r = client.post("/api/v1/boards", json={"name": "Работа", "description": "d"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Работа"
    assert body["archived_at"] is None


def test_create_board_validation_400(client):
    r = client.post("/api/v1/boards", json={"name": ""})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION"


def test_list_boards_with_task_count(client, board, board_full):
    make_task(client, board["id"], board_full["columns"][0]["id"])
    r = client.get("/api/v1/boards")
    assert r.status_code == 200
    assert r.json()[0]["task_count"] == 1


def test_get_board_full(client, board):
    r = client.get(f"/api/v1/boards/{board['id']}")
    assert r.status_code == 200
    body = r.json()
    assert [c["name"] for c in body["columns"]] == ["Backlog", "В работе", "Готово"]
    assert body["columns"][2]["is_final"] is True
    assert body["columns"][0]["tasks"] == []


def test_get_board_404(client):
    r = client.get("/api/v1/boards/нет")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_patch_board_and_archive(client, board):
    r = client.patch(f"/api/v1/boards/{board['id']}", json={"name": "Дом", "archived": True})
    assert r.status_code == 200
    assert r.json()["name"] == "Дом"
    assert r.json()["archived_at"] is not None
    assert client.get("/api/v1/boards").json() == []
    assert len(client.get("/api/v1/boards", params={"include_archived": True}).json()) == 1


def test_delete_board(client, board):
    assert client.delete(f"/api/v1/boards/{board['id']}").status_code == 204
    assert client.get(f"/api/v1/boards/{board['id']}").status_code == 404
