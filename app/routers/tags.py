from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.db.protocol import Repository
from app.dependencies.auth import verify_api_key
from app.dependencies.db import get_repository
from app.routers.deps import handle_repo_errors
from app.schemas.entities import Tag, TagCreate, TagUpdate

router = APIRouter(prefix="/v1/clients/{client_id}/tags", tags=["tags"])


@router.get("", response_model=list[Tag])
@handle_repo_errors
async def list_tags(
    client_id: str,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> list[Tag]:
    return await repo.list_tags(client_id)


@router.post("", response_model=Tag, status_code=status.HTTP_201_CREATED)
@handle_repo_errors
async def create_tag(
    client_id: str,
    body: TagCreate,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> Tag:
    return await repo.create_tag(client_id, body)


@router.get("/{tag_id}", response_model=Tag)
@handle_repo_errors
async def get_tag(
    client_id: str,
    tag_id: str,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> Tag:
    return await repo.get_tag(client_id, tag_id)


@router.patch("/{tag_id}", response_model=Tag)
@handle_repo_errors
async def update_tag(
    client_id: str,
    tag_id: str,
    body: TagUpdate,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> Tag:
    return await repo.update_tag(client_id, tag_id, body)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_repo_errors
async def delete_tag(
    client_id: str,
    tag_id: str,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> None:
    await repo.delete_tag(client_id, tag_id)
