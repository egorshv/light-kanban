from tests.contract.conftest import make_task


def test_create_task(client, board, board_full):
    col = board_full["columns"][0]
    task = make_task(client, board["id"], col["id"], "Первая", priority="high")
    assert task["position"] == 0
    assert task["priority"] == "high"
    assert task["wip_warning"] is None


def test_create_task_wip_warning(client, board, board_full):
    col = board_full["columns"][0]
    client.patch(f"/api/v1/columns/{col['id']}", json={"wip_limit": 1})
    make_task(client, board["id"], col["id"])
    task = make_task(client, board["id"], col["id"])
    assert task["wip_warning"]["task_count"] == 2
    assert task["wip_warning"]["wip_limit"] == 1


def test_create_task_validation_400(client, board, board_full):
    r = client.post(
        "/api/v1/tasks",
        json={
            "board_id": board["id"],
            "column_id": board_full["columns"][0]["id"],
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION"


def test_get_task_with_links(client, board, board_full):
    col = board_full["columns"][0]
    a = make_task(client, board["id"], col["id"], "A")
    b = make_task(client, board["id"], col["id"], "B")
    client.post(
        "/api/v1/links",
        json={
            "source_task_id": a["id"],
            "target_task_id": b["id"],
            "link_type": "blocks",
        },
    )
    r = client.get(f"/api/v1/tasks/{b['id']}")
    assert r.status_code == 200
    link = r.json()["links"][0]
    assert link["direction"] == "in"
    assert link["other_task"]["title"] == "A"


def test_patch_task(client, board, board_full):
    task = make_task(client, board["id"], board_full["columns"][0]["id"])
    r = client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={
            "title": "Новый",
            "due_date": "2026-08-01",
        },
    )
    assert r.status_code == 200
    assert (r.json()["title"], r.json()["due_date"]) == ("Новый", "2026-08-01")


def test_move_task_to_final(client, board, board_full):
    src, final = board_full["columns"][0], board_full["columns"][2]
    task = make_task(client, board["id"], src["id"])
    r = client.post(
        f"/api/v1/tasks/{task['id']}/move",
        json={
            "column_id": final["id"],
            "position": 0,
        },
    )
    assert r.status_code == 200
    assert r.json()["column_id"] == final["id"]
    assert r.json()["completed_at"] is not None


def test_delete_task(client, board, board_full):
    task = make_task(client, board["id"], board_full["columns"][0]["id"])
    assert client.delete(f"/api/v1/tasks/{task['id']}").status_code == 204
    assert client.get(f"/api/v1/tasks/{task['id']}").status_code == 404


def test_board_tasks_filters(client, board, board_full):
    col = board_full["columns"][0]["id"]
    make_task(client, board["id"], col, "Купить хлеб", due_date="2026-07-01")
    make_task(client, board["id"], col, "Помыть посуду", priority="high")
    url = f"/api/v1/boards/{board['id']}/tasks"
    assert [t["title"] for t in client.get(url, params={"q": "хлеб"}).json()] == ["Купить хлеб"]
    assert len(client.get(url, params={"priority": "high"}).json()) == 1
    assert len(client.get(url, params={"due_before": "2026-07-15"}).json()) == 1
    assert len(client.get(url).json()) == 2


def test_task_404(client):
    assert client.get("/api/v1/tasks/нет").status_code == 404
