import pytest

from app.errors import NotFound, ValidationError
from app.services import boards, links, tasks
from tests.helpers import make_board, make_task


def test_create_board_with_default_columns(conn, uid):
    board = make_board(conn, uid)
    full = boards.get_board_full(conn, uid, board["id"])
    assert [c["name"] for c in full["columns"]] == ["Backlog", "В работе", "Готово"]
    assert [c["position"] for c in full["columns"]] == [0, 1, 2]
    assert [c["is_final"] for c in full["columns"]] == [0, 0, 1]


def test_create_board_empty(conn, uid):
    board = boards.create_board(conn, uid, "Пустая", with_default_columns=False)
    assert boards.get_board_full(conn, uid, board["id"])["columns"] == []


def test_board_name_validation(conn, uid):
    with pytest.raises(ValidationError):
        boards.create_board(conn, uid, "")
    with pytest.raises(ValidationError):
        boards.create_board(conn, uid, "x" * 101)


def test_update_board(conn, uid):
    board = make_board(conn, uid)
    updated = boards.update_board(conn, uid, board["id"], {"name": "Новое", "description": "опис."})
    assert updated["name"] == "Новое"
    assert updated["description"] == "опис."
    assert updated["updated_at"] >= board["updated_at"]


def test_archive_board_hides_from_list(conn, uid):
    board = make_board(conn, uid)
    boards.update_board(conn, uid, board["id"], {"archived": True})
    assert boards.list_boards(conn, uid) == []
    archived = boards.list_boards(conn, uid, include_archived=True)
    assert [b["id"] for b in archived] == [board["id"]]
    assert archived[0]["archived_at"] is not None
    boards.update_board(conn, uid, board["id"], {"archived": False})
    assert len(boards.list_boards(conn, uid)) == 1


def test_list_boards_task_count(conn, uid):
    board = make_board(conn, uid)
    full = boards.get_board_full(conn, uid, board["id"])
    make_task(conn, uid, board["id"], full["columns"][0]["id"])
    assert boards.list_boards(conn, uid)[0]["task_count"] == 1


def test_delete_board_cascades(conn, uid):
    a = make_board(conn, uid, "A")
    b = make_board(conn, uid, "B")
    col_a = boards.get_board_full(conn, uid, a["id"])["columns"][0]
    col_b = boards.get_board_full(conn, uid, b["id"])["columns"][0]
    task_a = make_task(conn, uid, a["id"], col_a["id"])
    task_b = make_task(conn, uid, b["id"], col_b["id"])
    links.create_link(conn, uid, task_a["id"], task_b["id"], "relates_to")  # кросс-досочная

    boards.delete_board(conn, uid, a["id"])

    with pytest.raises(NotFound):
        boards.get_board(conn, uid, a["id"])
    with pytest.raises(NotFound):
        tasks.get_task(conn, uid, task_a["id"])
    # задача второй доски цела, кросс-досочная связь снята каскадом
    assert tasks.get_task_with_links(conn, uid, task_b["id"])["links"] == []
