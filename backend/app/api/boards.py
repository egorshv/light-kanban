from fastapi import APIRouter, Depends

from app.api.deps import get_conn
from app.schemas.boards import BoardCreate, BoardFull, BoardListItem, BoardOut, BoardPatch
from app.services import boards as boards_service

router = APIRouter(tags=["boards"])


@router.get("/boards", response_model=list[BoardListItem])
def list_boards(include_archived: bool = False, conn=Depends(get_conn)):
    return boards_service.list_boards(conn, include_archived)


@router.post("/boards", response_model=BoardOut, status_code=201)
def create_board(body: BoardCreate, conn=Depends(get_conn)):
    return boards_service.create_board(conn, body.name, body.description, body.with_default_columns)


@router.get("/boards/{board_id}", response_model=BoardFull)
def get_board(board_id: str, conn=Depends(get_conn)):
    return boards_service.get_board_full(conn, board_id)


@router.patch("/boards/{board_id}", response_model=BoardOut)
def update_board(board_id: str, body: BoardPatch, conn=Depends(get_conn)):
    return boards_service.update_board(conn, board_id, body.model_dump(exclude_unset=True))


@router.delete("/boards/{board_id}", status_code=204)
def delete_board(board_id: str, conn=Depends(get_conn)):
    boards_service.delete_board(conn, board_id)
