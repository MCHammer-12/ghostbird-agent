from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.db.protocol import Repository
from app.dependencies.auth import verify_api_key
from app.dependencies.db import get_repository
from app.routers.deps import handle_repo_errors
from app.schemas.entities import Client, ClientCreate, ClientUpdate

router = APIRouter(prefix="/v1/clients", tags=["clients"])


@router.get("", response_model=list[Client])
@handle_repo_errors
async def list_clients(
    q: str | None = None,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> list[Client]:
    return await repo.list_clients(q)


@router.post("", response_model=Client, status_code=status.HTTP_201_CREATED)
@handle_repo_errors
async def create_client(
    body: ClientCreate,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> Client:
    return await repo.create_client(body)


@router.get("/{client_id}", response_model=Client)
@handle_repo_errors
async def get_client(
    client_id: str,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> Client:
    return await repo.get_client(client_id)


@router.patch("/{client_id}", response_model=Client)
@handle_repo_errors
async def update_client(
    client_id: str,
    body: ClientUpdate,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> Client:
    return await repo.update_client(client_id, body)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_repo_errors
async def delete_client(
    client_id: str,
    _: None = Depends(verify_api_key),
    repo: Repository = Depends(get_repository),
) -> None:
    await repo.delete_client(client_id)
