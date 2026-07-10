import pytest

from app.errors import Conflict, ValidationError
from app.services import boards, columns, tasks
from tests.helpers import column_ids, make_board, make_column, make_task


@pytest.fixture
def board(conn):
    return make_board(conn)


def test_create_column_appends(conn, board):
    col = make_column(conn, board["id"], "Новая")
    assert col["position"] == 3


def test_wip_limit_must_be_positive(conn, board):
    with pytest.raises(ValidationError):
        make_column(conn, board["id"], wip_limit=0)


def test_name_length_validation(conn, board):
    with pytest.raises(ValidationError):
        make_column(conn, board["id"], "x" * 51)


def test_update_column(conn, board):
    col_id = column_ids(conn, board["id"])[0]
    updated = columns.update_column(
        conn, col_id, {"name": "Новое имя", "wip_limit": 3, "is_final": True}
    )
    assert (updated["name"], updated["wip_limit"], updated["is_final"]) == ("Новое имя", 3, 1)
    updated = columns.update_column(conn, col_id, {"wip_limit": None})
    assert updated["wip_limit"] is None


def test_move_column_renumbers(conn, board):
    ids = column_ids(conn, board["id"])
    columns.move_column(conn, ids[2], 0)
    full = boards.get_board_full(conn, board["id"])
    assert [c["id"] for c in full["columns"]] == [ids[2], ids[0], ids[1]]
    assert [c["position"] for c in full["columns"]] == [0, 1, 2]


def test_delete_last_column_conflict(conn):
    b = boards.create_board(conn, "Б", with_default_columns=False)
    col = make_column(conn, b["id"])
    with pytest.raises(Conflict) as e:
        columns.delete_column(conn, col["id"])
    assert e.value.code == "LAST_COLUMN"


def test_delete_column_with_tasks_requires_target(conn, board):
    ids = column_ids(conn, board["id"])
    make_task(conn, board["id"], ids[0])
    with pytest.raises(Conflict) as e:
        columns.delete_column(conn, ids[0])
    assert e.value.code == "COLUMN_NOT_EMPTY"


def test_delete_empty_column_renumbers_rest(conn, board):
    ids = column_ids(conn, board["id"])
    columns.delete_column(conn, ids[0])
    full = boards.get_board_full(conn, board["id"])
    assert [c["id"] for c in full["columns"]] == [ids[1], ids[2]]
    assert [c["position"] for c in full["columns"]] == [0, 1]


def test_delete_column_moves_tasks_to_target(conn, board):
    ids = column_ids(conn, board["id"])
    t1 = make_task(conn, board["id"], ids[0], "t1")
    t2 = make_task(conn, board["id"], ids[0], "t2")
    t3 = make_task(conn, board["id"], ids[1], "t3")

    columns.delete_column(conn, ids[0], move_tasks_to=ids[1])

    full = boards.get_board_full(conn, board["id"])
    target = full["columns"][0]
    assert target["id"] == ids[1]
    assert [t["id"] for t in target["tasks"]] == [t3["id"], t1["id"], t2["id"]]
    assert [t["position"] for t in target["tasks"]] == [0, 1, 2]


def test_delete_column_moving_into_final_completes_tasks(conn, board):
    ids = column_ids(conn, board["id"])
    t1 = make_task(conn, board["id"], ids[0])
    columns.delete_column(conn, ids[0], move_tasks_to=ids[2])  # «Готово» — is_final
    assert tasks.get_task(conn, t1["id"])["completed_at"] is not None


def test_delete_column_target_on_other_board(conn, board):
    other = make_board(conn, "Другая")
    ids = column_ids(conn, board["id"])
    make_task(conn, board["id"], ids[0])
    with pytest.raises(Conflict):
        columns.delete_column(conn, ids[0], move_tasks_to=column_ids(conn, other["id"])[0])
