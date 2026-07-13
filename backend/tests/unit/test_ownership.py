"""Изоляция данных: пользователь B не видит и не трогает сущности пользователя A."""

import pytest

from app.errors import NotFound
from app.services import auth, boards, columns, links, tasks
from tests.helpers import column_ids, make_board, make_task


@pytest.fixture
def uid_b(conn, uid):
    return auth.sign_up(conn, "other@test.ru", "password2")["id"]


@pytest.fixture
def setup_a(conn, uid):
    board = make_board(conn, uid)
    cols = column_ids(conn, uid, board["id"])
    task = make_task(conn, uid, board["id"], cols[0])
    return board, cols, task


def test_board_ops_hidden_from_other_user(conn, uid, uid_b, setup_a):
    board, cols, task = setup_a
    with pytest.raises(NotFound):
        boards.get_board(conn, uid_b, board["id"])
    with pytest.raises(NotFound):
        boards.get_board_full(conn, uid_b, board["id"])
    with pytest.raises(NotFound):
        boards.update_board(conn, uid_b, board["id"], {"name": "Чужое"})
    with pytest.raises(NotFound):
        boards.delete_board(conn, uid_b, board["id"])


def test_column_ops_hidden_from_other_user(conn, uid, uid_b, setup_a):
    board, cols, task = setup_a
    with pytest.raises(NotFound):
        columns.create_column(conn, uid_b, board["id"], "Взлом")
    with pytest.raises(NotFound):
        columns.get_column(conn, uid_b, cols[0])
    with pytest.raises(NotFound):
        columns.move_column(conn, uid_b, cols[0], 1)
    with pytest.raises(NotFound):
        columns.delete_column(conn, uid_b, cols[0])
    # цель переноса задач при удалении тоже должна быть своей
    board_b = make_board(conn, uid_b)
    col_b = column_ids(conn, uid_b, board_b["id"])[0]
    with pytest.raises(NotFound):
        columns.delete_column(conn, uid, cols[0], move_tasks_to=col_b)


def test_task_ops_hidden_from_other_user(conn, uid, uid_b, setup_a):
    board, cols, task = setup_a
    with pytest.raises(NotFound):
        tasks.create_task(conn, uid_b, board["id"], cols[0], "Чужая задача")
    with pytest.raises(NotFound):
        tasks.get_task(conn, uid_b, task["id"])
    with pytest.raises(NotFound):
        tasks.get_task_with_links(conn, uid_b, task["id"])
    with pytest.raises(NotFound):
        tasks.update_task(conn, uid_b, task["id"], {"title": "Взлом"})
    with pytest.raises(NotFound):
        tasks.move_task(conn, uid_b, task["id"], cols[1], 0)
    with pytest.raises(NotFound):
        tasks.delete_task(conn, uid_b, task["id"])
    with pytest.raises(NotFound):
        tasks.search_tasks(conn, uid_b, board["id"])


def test_link_ops_respect_ownership(conn, uid, uid_b, setup_a):
    board, cols, task = setup_a
    board_b = make_board(conn, uid_b)
    col_b = column_ids(conn, uid_b, board_b["id"])[0]
    task_b = make_task(conn, uid_b, board_b["id"], col_b)
    # связь с чужой задачей невозможна в обе стороны
    with pytest.raises(NotFound):
        links.create_link(conn, uid, task["id"], task_b["id"], "blocks")
    with pytest.raises(NotFound):
        links.create_link(conn, uid_b, task_b["id"], task["id"], "blocks")
    # своя кросс-досочная связь — можно (§2), чужой её не удалит
    board2 = make_board(conn, uid, "Вторая")
    task2 = make_task(conn, uid, board2["id"], column_ids(conn, uid, board2["id"])[0])
    link = links.create_link(conn, uid, task["id"], task2["id"], "relates_to")
    with pytest.raises(NotFound):
        links.delete_link(conn, uid_b, link["id"])
    links.delete_link(conn, uid, link["id"])


def test_list_boards_isolated(conn, uid, uid_b):
    make_board(conn, uid, "A1")
    make_board(conn, uid_b, "B1")
    assert [b["name"] for b in boards.list_boards(conn, uid)] == ["A1"]
    assert [b["name"] for b in boards.list_boards(conn, uid_b)] == ["B1"]
