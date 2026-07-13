from app.services import boards, columns, tasks


def make_board(conn, uid, name="Доска", **kw):
    return boards.create_board(conn, uid, name, **kw)


def make_column(conn, uid, board_id, name="Колонка", **kw):
    return columns.create_column(conn, uid, board_id, name, **kw)


def make_task(conn, uid, board_id, column_id, title="Задача", **kw):
    task, _ = tasks.create_task(conn, uid, board_id, column_id, title, **kw)
    return task


def column_ids(conn, uid, board_id):
    return [c["id"] for c in boards.get_board_full(conn, uid, board_id)["columns"]]
