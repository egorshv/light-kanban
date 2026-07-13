from fastapi import APIRouter, Depends

from app.api.deps import current_user_id, get_conn
from app.schemas.links import LinkCreate, LinkOut
from app.services import links as links_service

router = APIRouter(tags=["links"])


@router.post("/links", response_model=LinkOut, status_code=201)
def create_link(body: LinkCreate, user_id: str = Depends(current_user_id), conn=Depends(get_conn)):
    return links_service.create_link(
        conn, user_id, body.source_task_id, body.target_task_id, body.link_type
    )


@router.delete("/links/{link_id}", status_code=204)
def delete_link(link_id: str, user_id: str = Depends(current_user_id), conn=Depends(get_conn)):
    links_service.delete_link(conn, user_id, link_id)
