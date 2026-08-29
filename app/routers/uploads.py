from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.db.protocol import Repository
from app.dependencies.auth import verify_api_key
from app.dependencies.db import get_repository
from app.routers.deps import handle_repo_errors
from app.schemas.entities import (
    Tag,
    Upload,
    UploadCreate,
    UploadTagsReplace,
    UploadUpdate,
)

router = APIRouter(prefix="/v1/clients/{client_id}/uploads", tags=["uploads"])


@router.get("", response_model=list[Upload])
@handle_repo_errors
async def list_uploads(
    client_id: str,
    tag_id: str | None = None,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> list[Upload]:
    return await repo.list_uploads(client_id, tag_id)


@router.post("", response_model=Upload, status_code=status.HTTP_201_CREATED)
@handle_repo_errors
async def create_upload(
    client_id: str,
    body: UploadCreate,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> Upload:
    return await repo.create_upload(client_id, body)


@router.get("/{upload_id}", response_model=Upload)
@handle_repo_errors
async def get_upload(
    client_id: str,
    upload_id: str,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> Upload:
    return await repo.get_upload(client_id, upload_id)


@router.patch("/{upload_id}", response_model=Upload)
@handle_repo_errors
async def update_upload(
    client_id: str,
    upload_id: str,
    body: UploadUpdate,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> Upload:
    return await repo.update_upload(client_id, upload_id, body)


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_repo_errors
async def delete_upload(
    client_id: str,
    upload_id: str,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> None:
    await repo.delete_upload(client_id, upload_id)


@router.get("/{upload_id}/tags", response_model=list[Tag])
@handle_repo_errors
async def list_upload_tags(
    client_id: str,
    upload_id: str,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> list[Tag]:
    return await repo.list_upload_tags(client_id, upload_id)


@router.put("/{upload_id}/tags", response_model=list[Tag])
@handle_repo_errors
async def replace_upload_tags(
    client_id: str,
    upload_id: str,
    body: UploadTagsReplace,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> list[Tag]:
    return await repo.replace_upload_tags(client_id, upload_id, body.tag_ids)


@router.post(
    "/{upload_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@handle_repo_errors
async def attach_upload_tag(
    client_id: str,
    upload_id: str,
    tag_id: str,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> None:
    await repo.attach_upload_tag(client_id, upload_id, tag_id)


@router.delete(
    "/{upload_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@handle_repo_errors
async def detach_upload_tag(
    client_id: str,
    upload_id: str,
    tag_id: str,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> None:
    await repo.detach_upload_tag(client_id, upload_id, tag_id)
