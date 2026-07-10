import pytest

from tests.contract.conftest import make_task


@pytest.fixture
def two_tasks(client, board, board_full):
    col = board_full["columns"][0]["id"]
    return (
        make_task(client, board["id"], col, "A"),
        make_task(client, board["id"], col, "B"),
    )


def _link(client, source, target, link_type="blocks"):
    return client.post(
        "/api/v1/links",
        json={
            "source_task_id": source["id"],
            "target_task_id": target["id"],
            "link_type": link_type,
        },
    )


def test_create_link(client, two_tasks):
    a, b = two_tasks
    r = _link(client, a, b)
    assert r.status_code == 201
    assert r.json()["link_type"] == "blocks"


def test_self_link_422(client, two_tasks):
    a, _ = two_tasks
    r = _link(client, a, a)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "SELF_LINK"


def test_duplicate_link_422(client, two_tasks):
    a, b = two_tasks
    _link(client, a, b)
    r = _link(client, a, b)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "DUPLICATE_LINK"


def test_cycle_422(client, two_tasks):
    a, b = two_tasks
    _link(client, a, b)
    r = _link(client, b, a)
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "LINK_CYCLE"
    assert "цикл" in body["message"]


def test_second_parent_422(client, board, board_full, two_tasks):
    a, b = two_tasks
    c = make_task(client, board["id"], board_full["columns"][0]["id"], "C")
    _link(client, a, b, "subtask_of")
    r = _link(client, a, c, "subtask_of")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "PARENT_EXISTS"


def test_bad_link_type_400(client, two_tasks):
    a, b = two_tasks
    r = client.post(
        "/api/v1/links",
        json={
            "source_task_id": a["id"],
            "target_task_id": b["id"],
            "link_type": "loves",
        },
    )
    assert r.status_code == 400


def test_delete_link(client, two_tasks):
    a, b = two_tasks
    link = _link(client, a, b).json()
    assert client.delete(f"/api/v1/links/{link['id']}").status_code == 204
    assert client.delete(f"/api/v1/links/{link['id']}").status_code == 404
