import pytest

from app.errors import Conflict, NotFound, ValidationError
from app.services import columns, tasks
from tests.helpers import column_ids, make_board, make_task


@pytest.fixture
def board(conn, uid):
    return make_board(conn, uid)


@pytest.fixture
def cols(conn, uid, board):
    return column_ids(conn, uid, board["id"])


def test_create_task_defaults_and_position(conn, uid, board, cols):
    t1 = make_task(conn, uid, board["id"], cols[0], "Первая")
    t2 = make_task(conn, uid, board["id"], cols[0], "Вторая")
    assert (t1["position"], t2["position"]) == (0, 1)
    assert t1["priority"] == "normal"
    assert t1["completed_at"] is None
    assert t1["description"] == ""


def test_create_in_final_column_sets_completed(conn, uid, board, cols):
    t = make_task(conn, uid, board["id"], cols[2])  # «Готово» — is_final
    assert t["completed_at"] is not None


def test_create_validation(conn, uid, board, cols):
    with pytest.raises(ValidationError):
        make_task(conn, uid, board["id"], cols[0], "")
    with pytest.raises(ValidationError):
        make_task(conn, uid, board["id"], cols[0], priority="огонь")
    with pytest.raises(ValidationError):
        make_task(conn, uid, board["id"], cols[0], due_date="не дата")


def test_create_in_foreign_column_conflict(conn, uid, board, cols):
    other = make_board(conn, uid, "Другая")
    with pytest.raises(Conflict):
        make_task(conn, uid, other["id"], cols[0])


def test_wip_warning_on_create(conn, uid, board, cols):
    columns.update_column(conn, uid, cols[0], {"wip_limit": 1})
    _, warning = tasks.create_task(conn, uid, board["id"], cols[0], "t1")
    assert warning is None
    _, warning = tasks.create_task(conn, uid, board["id"], cols[0], "t2")
    assert warning == {
        "column_id": cols[0],
        "column_name": "Backlog",
        "wip_limit": 1,
        "task_count": 2,
    }


def test_move_within_column(conn, uid, board, cols):
    t1 = make_task(conn, uid, board["id"], cols[0], "t1")
    t2 = make_task(conn, uid, board["id"], cols[0], "t2")
    t3 = make_task(conn, uid, board["id"], cols[0], "t3")
    tasks.move_task(conn, uid, t3["id"], cols[0], 0)
    rows = [(t["id"], t["position"]) for t in _column_tasks(conn, uid, cols[0])]
    assert rows == [(t3["id"], 0), (t1["id"], 1), (t2["id"], 2)]


def test_move_between_columns_renumbers_both(conn, uid, board, cols):
    t1 = make_task(conn, uid, board["id"], cols[0], "t1")
    t2 = make_task(conn, uid, board["id"], cols[0], "t2")
    t3 = make_task(conn, uid, board["id"], cols[1], "t3")
    moved, warning = tasks.move_task(conn, uid, t1["id"], cols[1], 0)
    assert (moved["column_id"], moved["position"]) == (cols[1], 0)
    assert warning is None
    assert [(t["id"], t["position"]) for t in _column_tasks(conn, uid, cols[0])] == [(t2["id"], 0)]
    assert [(t["id"], t["position"]) for t in _column_tasks(conn, uid, cols[1])] == [
        (t1["id"], 0),
        (t3["id"], 1),
    ]


def test_move_position_clamped(conn, uid, board, cols):
    t1 = make_task(conn, uid, board["id"], cols[0])
    moved, _ = tasks.move_task(conn, uid, t1["id"], cols[1], 99)
    assert moved["position"] == 0


def test_move_to_final_sets_completed_and_back_clears(conn, uid, board, cols):
    t = make_task(conn, uid, board["id"], cols[0])
    moved, _ = tasks.move_task(conn, uid, t["id"], cols[2], 0)
    assert moved["completed_at"] is not None
    moved, _ = tasks.move_task(conn, uid, moved["id"], cols[0], 0)
    assert moved["completed_at"] is None


def test_move_wip_warning(conn, uid, board, cols):
    columns.update_column(conn, uid, cols[1], {"wip_limit": 1})
    make_task(conn, uid, board["id"], cols[1])
    t = make_task(conn, uid, board["id"], cols[0])
    _, warning = tasks.move_task(conn, uid, t["id"], cols[1], 0)
    assert warning is not None and warning["task_count"] == 2


def test_move_cross_board_rejected(conn, uid, board, cols):
    other = make_board(conn, uid, "Другая")
    t = make_task(conn, uid, board["id"], cols[0])
    with pytest.raises(Conflict):
        tasks.move_task(conn, uid, t["id"], column_ids(conn, uid, other["id"])[0], 0)


def test_update_task(conn, uid, board, cols):
    t = make_task(conn, uid, board["id"], cols[0])
    updated = tasks.update_task(
        conn,
        uid,
        t["id"],
        {
            "title": "Новый",
            "priority": "urgent",
            "due_date": "2026-08-01",
        },
    )
    assert (updated["title"], updated["priority"], updated["due_date"]) == (
        "Новый",
        "urgent",
        "2026-08-01",
    )
    with pytest.raises(ValidationError):
        tasks.update_task(conn, uid, t["id"], {"title": ""})


def test_delete_task_renumbers_and_cascades_links(conn, uid, board, cols):
    from app.services import links as links_service

    t1 = make_task(conn, uid, board["id"], cols[0], "t1")
    t2 = make_task(conn, uid, board["id"], cols[0], "t2")
    links_service.create_link(conn, uid, t1["id"], t2["id"], "blocks")
    tasks.delete_task(conn, uid, t1["id"])
    with pytest.raises(NotFound):
        tasks.get_task(conn, uid, t1["id"])
    assert [(t["id"], t["position"]) for t in _column_tasks(conn, uid, cols[0])] == [(t2["id"], 0)]
    assert tasks.get_task_with_links(conn, uid, t2["id"])["links"] == []


def test_search(conn, uid, board, cols):
    make_task(conn, uid, board["id"], cols[0], "Купить хлеб", due_date="2026-07-01")
    make_task(conn, uid, board["id"], cols[0], "Помыть посуду", priority="high")
    # регистронезависимо для кириллицы
    assert [t["title"] for t in tasks.search_tasks(conn, uid, board["id"], q="ХЛЕБ")] == [
        "Купить хлеб"
    ]
    assert len(tasks.search_tasks(conn, uid, board["id"], priority="high")) == 1
    assert len(tasks.search_tasks(conn, uid, board["id"], due_before="2026-07-15")) == 1
    assert len(tasks.search_tasks(conn, uid, board["id"])) == 2
    with pytest.raises(NotFound):
        tasks.search_tasks(conn, uid, "нет-такой", q="x")


def _column_tasks(conn, uid, column_id):
    from app.repo import tasks as tasks_repo

    return [dict(r) for r in tasks_repo.list_by_column(conn, column_id)]
