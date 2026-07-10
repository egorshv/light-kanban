from fastapi import APIRouter, Depends

from app.api.deps import get_conn
from app.schemas.columns import ColumnCreate, ColumnMove, ColumnOut, ColumnPatch
from app.services import columns as columns_service

router = APIRouter(tags=["columns"])


@router.post("/boards/{board_id}/columns", response_model=ColumnOut, status_code=201)
def create_column(board_id: str, body: ColumnCreate, conn=Depends(get_conn)):
    return columns_service.create_column(
        conn, board_id, body.name, body.color, body.wip_limit, body.is_final
    )


@router.patch("/columns/{column_id}", response_model=ColumnOut)
def update_column(column_id: str, body: ColumnPatch, conn=Depends(get_conn)):
    return columns_service.update_column(conn, column_id, body.model_dump(exclude_unset=True))


@router.post("/columns/{column_id}/move", response_model=ColumnOut)
def move_column(column_id: str, body: ColumnMove, conn=Depends(get_conn)):
    return columns_service.move_column(conn, column_id, body.position)


@router.delete("/columns/{column_id}", status_code=204)
def delete_column(column_id: str, move_tasks_to: str | None = None, conn=Depends(get_conn)):
    columns_service.delete_column(conn, column_id, move_tasks_to)
