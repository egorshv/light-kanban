import pytest

from app.errors import DomainRuleViolation, NotFound
from app.services import boards, links, tasks
from tests.helpers import column_ids, make_board, make_task


@pytest.fixture
def board(conn, uid):
    return make_board(conn, uid)


@pytest.fixture
def col(conn, uid, board):
    return column_ids(conn, uid, board["id"])[0]


def _three(conn, uid, board, col):
    return [make_task(conn, uid, board["id"], col, name) for name in ("A", "B", "C")]


def test_self_link_rejected(conn, uid, board, col):
    t = make_task(conn, uid, board["id"], col)
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, uid, t["id"], t["id"], "blocks")
    assert e.value.code == "SELF_LINK"


def test_duplicate_rejected(conn, uid, board, col):
    a, b, _ = _three(conn, uid, board, col)
    links.create_link(conn, uid, a["id"], b["id"], "blocks")
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, uid, a["id"], b["id"], "blocks")
    assert e.value.code == "DUPLICATE_LINK"


def test_relates_to_reverse_is_duplicate(conn, uid, board, col):
    a, b, _ = _three(conn, uid, board, col)
    links.create_link(conn, uid, a["id"], b["id"], "relates_to")
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, uid, b["id"], a["id"], "relates_to")
    assert e.value.code == "DUPLICATE_LINK"


def test_duplicates_reverse_allowed(conn, uid, board, col):
    a, b, _ = _three(conn, uid, board, col)
    links.create_link(conn, uid, a["id"], b["id"], "duplicates")
    links.create_link(conn, uid, b["id"], a["id"], "duplicates")  # направленный тип — не дубликат


def test_subtask_single_parent(conn, uid, board, col):
    a, b, c = _three(conn, uid, board, col)
    links.create_link(conn, uid, a["id"], b["id"], "subtask_of")
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, uid, a["id"], c["id"], "subtask_of")
    assert e.value.code == "PARENT_EXISTS"


def test_blocks_cycle_rejected(conn, uid, board, col):
    a, b, c = _three(conn, uid, board, col)
    links.create_link(conn, uid, a["id"], b["id"], "blocks")
    links.create_link(conn, uid, b["id"], c["id"], "blocks")
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, uid, c["id"], a["id"], "blocks")
    assert e.value.code == "LINK_CYCLE"
    assert "цикл" in e.value.message


def test_subtask_cycle_rejected(conn, uid, board, col):
    a, b, _ = _three(conn, uid, board, col)
    links.create_link(conn, uid, a["id"], b["id"], "subtask_of")
    with pytest.raises(DomainRuleViolation) as e:
        links.create_link(conn, uid, b["id"], a["id"], "subtask_of")
    assert e.value.code == "LINK_CYCLE"


def test_cycle_check_is_per_type(conn, uid, board, col):
    # цикл считается по рёбрам одного типа: blocks A→B не мешает subtask B→A
    a, b, _ = _three(conn, uid, board, col)
    links.create_link(conn, uid, a["id"], b["id"], "blocks")
    links.create_link(conn, uid, b["id"], a["id"], "subtask_of")


def test_cross_board_link_allowed(conn, uid, board, col):
    other = make_board(conn, uid, "Другая")
    a = make_task(conn, uid, board["id"], col)
    b = make_task(conn, uid, other["id"], column_ids(conn, uid, other["id"])[0])
    link = links.create_link(conn, uid, a["id"], b["id"], "relates_to")
    assert link["link_type"] == "relates_to"


def test_delete_link(conn, uid, board, col):
    a, b, _ = _three(conn, uid, board, col)
    link = links.create_link(conn, uid, a["id"], b["id"], "blocks")
    links.delete_link(conn, uid, link["id"])
    with pytest.raises(NotFound):
        links.delete_link(conn, uid, link["id"])


def test_links_grouped_with_direction(conn, uid, board, col):
    a, b, _ = _three(conn, uid, board, col)
    links.create_link(conn, uid, a["id"], b["id"], "blocks")
    out = tasks.get_task_with_links(conn, uid, a["id"])["links"]
    inc = tasks.get_task_with_links(conn, uid, b["id"])["links"]
    assert out[0]["direction"] == "out" and out[0]["other_task"]["id"] == b["id"]
    assert inc[0]["direction"] == "in" and inc[0]["other_task"]["id"] == a["id"]


def test_blocked_flag_on_board(conn, uid, board, col):
    a, b, _ = _three(conn, uid, board, col)
    links.create_link(conn, uid, a["id"], b["id"], "blocks")

    def blocked(task_id):
        full = boards.get_board_full(conn, uid, board["id"])
        by_id = {t["id"]: t for c in full["columns"] for t in c["tasks"]}
        return by_id[task_id]["is_blocked"]

    assert blocked(b["id"]) == 1 and blocked(a["id"]) == 0
    # завершённый блокер перестаёт блокировать (US-D4: активные блокеры)
    final_col = column_ids(conn, uid, board["id"])[2]
    tasks.move_task(conn, uid, a["id"], final_col, 0)
    assert blocked(b["id"]) == 0
