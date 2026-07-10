from tests.contract.conftest import make_task


def test_create_column(client, board):
    r = client.post(f"/api/v1/boards/{board['id']}/columns", json={"name": "Ревью"})
    assert r.status_code == 201
    assert r.json()["position"] == 3
    assert r.json()["is_final"] is False


def test_create_column_validation_400(client, board):
    r = client.post(f"/api/v1/boards/{board['id']}/columns", json={"name": "x", "wip_limit": 0})
    assert r.status_code == 400


def test_patch_column(client, board_full):
    col = board_full["columns"][0]
    r = client.patch(f"/api/v1/columns/{col['id']}", json={"wip_limit": 2, "color": "#ff0000"})
    assert r.status_code == 200
    assert (r.json()["wip_limit"], r.json()["color"]) == (2, "#ff0000")


def test_move_column(client, board, board_full):
    col = board_full["columns"][2]
    r = client.post(f"/api/v1/columns/{col['id']}/move", json={"position": 0})
    assert r.status_code == 200
    assert r.json()["position"] == 0
    names = [c["name"] for c in client.get(f"/api/v1/boards/{board['id']}").json()["columns"]]
    assert names == ["Готово", "Backlog", "В работе"]


def test_delete_column_with_tasks_409(client, board, board_full):
    col = board_full["columns"][0]
    make_task(client, board["id"], col["id"])
    r = client.delete(f"/api/v1/columns/{col['id']}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "COLUMN_NOT_EMPTY"


def test_delete_column_moving_tasks(client, board, board_full):
    src, dst = board_full["columns"][0], board_full["columns"][1]
    task = make_task(client, board["id"], src["id"])
    r = client.delete(f"/api/v1/columns/{src['id']}", params={"move_tasks_to": dst["id"]})
    assert r.status_code == 204
    full = client.get(f"/api/v1/boards/{board['id']}").json()
    assert len(full["columns"]) == 2
    assert full["columns"][0]["tasks"][0]["id"] == task["id"]


def test_delete_last_column_409(client, board, board_full):
    for col in board_full["columns"][:2]:
        assert client.delete(f"/api/v1/columns/{col['id']}").status_code == 204
    r = client.delete(f"/api/v1/columns/{board_full['columns'][2]['id']}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "LAST_COLUMN"


def test_column_404(client):
    assert client.patch("/api/v1/columns/нет", json={"name": "x"}).status_code == 404
