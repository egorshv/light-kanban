from app.services import boards, columns, tasks


def make_board(conn, name="Доска", **kw):
    return boards.create_board(conn, name, **kw)


def make_column(conn, board_id, name="Колонка", **kw):
    return columns.create_column(conn, board_id, name, **kw)


def make_task(conn, board_id, column_id, title="Задача", **kw):
    task, _ = tasks.create_task(conn, board_id, column_id, title, **kw)
    return task


def column_ids(conn, board_id):
    return [c["id"] for c in boards.get_board_full(conn, board_id)["columns"]]
