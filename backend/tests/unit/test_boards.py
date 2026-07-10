import pytest

from app.errors import NotFound, ValidationError
from app.services import boards, links, tasks
from tests.helpers import make_board, make_task


def test_create_board_with_default_columns(conn):
    board = make_board(conn)
    full = boards.get_board_full(conn, board["id"])
    assert [c["name"] for c in full["columns"]] == ["Backlog", "В работе", "Готово"]
    assert [c["position"] for c in full["columns"]] == [0, 1, 2]
    assert [c["is_final"] for c in full["columns"]] == [0, 0, 1]


def test_create_board_empty(conn):
    board = boards.create_board(conn, "Пустая", with_default_columns=False)
    assert boards.get_board_full(conn, board["id"])["columns"] == []


def test_board_name_validation(conn):
    with pytest.raises(ValidationError):
        boards.create_board(conn, "")
    with pytest.raises(ValidationError):
        boards.create_board(conn, "x" * 101)


def test_update_board(conn):
    board = make_board(conn)
    updated = boards.update_board(conn, board["id"], {"name": "Новое", "description": "опис."})
    assert updated["name"] == "Новое"
    assert updated["description"] == "опис."
    assert updated["updated_at"] >= board["updated_at"]


def test_archive_board_hides_from_list(conn):
    board = make_board(conn)
    boards.update_board(conn, board["id"], {"archived": True})
    assert boards.list_boards(conn) == []
    archived = boards.list_boards(conn, include_archived=True)
    assert [b["id"] for b in archived] == [board["id"]]
    assert archived[0]["archived_at"] is not None
    boards.update_board(conn, board["id"], {"archived": False})
    assert len(boards.list_boards(conn)) == 1


def test_list_boards_task_count(conn):
    board = make_board(conn)
    full = boards.get_board_full(conn, board["id"])
    make_task(conn, board["id"], full["columns"][0]["id"])
    assert boards.list_boards(conn)[0]["task_count"] == 1


def test_delete_board_cascades(conn):
    a = make_board(conn, "A")
    b = make_board(conn, "B")
    col_a = boards.get_board_full(conn, a["id"])["columns"][0]
    col_b = boards.get_board_full(conn, b["id"])["columns"][0]
    task_a = make_task(conn, a["id"], col_a["id"])
    task_b = make_task(conn, b["id"], col_b["id"])
    links.create_link(conn, task_a["id"], task_b["id"], "relates_to")  # кросс-досочная

    boards.delete_board(conn, a["id"])

    with pytest.raises(NotFound):
        boards.get_board(conn, a["id"])
    with pytest.raises(NotFound):
        tasks.get_task(conn, task_a["id"])
    # задача второй доски цела, кросс-досочная связь снята каскадом
    assert tasks.get_task_with_links(conn, task_b["id"])["links"] == []
