import pytest

from app.errors import DomainRuleViolation, NotFound
from app.services import boards, links, tasks
from tests.helpers import column_ids, make_board, make_task


@pytest.fixture
def board(conn):
    return make_board(conn)


@pytest.fixture
def col(conn, board):
    return column_ids(conn, board["id"])[0]


def _three(conn, board, col):
    return [make_task(conn, board["id"], col, name) for name in ("A", "B", "C")]


def test_self_link_rejected(conn, board, col):
    t = make_task(conn, board["id"], col)
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, t["id"], t["id"], "blocks")
    assert e.value.code == "SELF_LINK"


def test_duplicate_rejected(conn, board, col):
    a, b, _ = _three(conn, board, col)
    links.create_link(conn, a["id"], b["id"], "blocks")
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, a["id"], b["id"], "blocks")
    assert e.value.code == "DUPLICATE_LINK"


def test_relates_to_reverse_is_duplicate(conn, board, col):
    a, b, _ = _three(conn, board, col)
    links.create_link(conn, a["id"], b["id"], "relates_to")
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, b["id"], a["id"], "relates_to")
    assert e.value.code == "DUPLICATE_LINK"


def test_duplicates_reverse_allowed(conn, board, col):
    a, b, _ = _three(conn, board, col)
    links.create_link(conn, a["id"], b["id"], "duplicates")
    links.create_link(conn, b["id"], a["id"], "duplicates")  # направленный тип — не дубликат


def test_subtask_single_parent(conn, board, col):
    a, b, c = _three(conn, board, col)
    links.create_link(conn, a["id"], b["id"], "subtask_of")
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, a["id"], c["id"], "subtask_of")
    assert e.value.code == "PARENT_EXISTS"


def test_blocks_cycle_rejected(conn, board, col):
    a, b, c = _three(conn, board, col)
    links.create_link(conn, a["id"], b["id"], "blocks")
    links.create_link(conn, b["id"], c["id"], "blocks")
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, c["id"], a["id"], "blocks")
    assert e.value.code == "LINK_CYCLE"
    assert "цикл" in e.value.message


def test_subtask_cycle_rejected(conn, board, col):
    a, b, _ = _three(conn, board, col)
    links.create_link(conn, a["id"], b["id"], "subtask_of")
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, b["id"], a["id"], "subtask_of")
    assert e.value.code == "LINK_CYCLE"


def test_cycle_check_is_per_type(conn, board, col):
    # цикл считается по рёбрам одного типа: blocks A→B не мешает subtask B→A
    a, b, _ = _three(conn, board, col)
    links.create_link(conn, a["id"], b["id"], "blocks")
    links.create_link(conn, b["id"], a["id"], "subtask_of")


def test_cross_board_link_allowed(conn, board, col):
    other = make_board(conn, "Другая")
    a = make_task(conn, board["id"], col)
    b = make_task(conn, other["id"], column_ids(conn, other["id"])[0])
    link = links.create_link(conn, a["id"], b["id"], "relates_to")
    assert link["link_type"] == "relates_to"


def test_delete_link(conn, board, col):
    a, b, _ = _three(conn, board, col)
    link = links.create_link(conn, a["id"], b["id"], "blocks")
    links.delete_link(conn, link["id"])
    with pytest.raises(NotFound):
        links.delete_link(conn, link["id"])


def test_links_grouped_with_direction(conn, board, col):
    a, b, _ = _three(conn, board, col)
    links.create_link(conn, a["id"], b["id"], "blocks")
    out = tasks.get_task_with_links(conn, a["id"])["links"]
    inc = tasks.get_task_with_links(conn, b["id"])["links"]
    assert out[0]["direction"] == "out" and out[0]["other_task"]["id"] == b["id"]
    assert inc[0]["direction"] == "in" and inc[0]["other_task"]["id"] == a["id"]


def test_blocked_flag_on_board(conn, board, col):
    a, b, _ = _three(conn, board, col)
    links.create_link(conn, a["id"], b["id"], "blocks")

    def blocked(task_id):
        full = boards.get_board_full(conn, board["id"])
        by_id = {t["id"]: t for c in full["columns"] for t in c["tasks"]}
        return by_id[task_id]["is_blocked"]

    assert blocked(b["id"]) == 1 and blocked(a["id"]) == 0
    # завершённый блокер перестаёт блокировать (US-D4: активные блокеры)
    final_col = column_ids(conn, board["id"])[2]
    tasks.move_task(conn, a["id"], final_col, 0)
    assert blocked(b["id"]) == 0
