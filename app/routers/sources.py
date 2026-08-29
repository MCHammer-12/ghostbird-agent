"""Upload a source and check its ingestion job."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.dependencies.auth import require_client_access
from app.dependencies.services import get_retrieval_service
from app.schemas.api import (
    IngestionJobResponse,
    SourceUploadRequest,
    SourceUploadResponse,
)
from app.schemas.shared import IngestionStatus
from app.services.protocol import METADATA_IDEMPOTENCY_KEY, RetrievalService

router = APIRouter(prefix="/v1/clients/{client_id}", tags=["sources"])


@router.post(
    "/sources",
    response_model=SourceUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a source for a client",
)
async def upload_source(
    body: SourceUploadRequest,
    client_id: str = Depends(require_client_access),
    settings: Settings = Depends(get_settings),
    service: RetrievalService = Depends(get_retrieval_service),
) -> SourceUploadResponse:
    if body.client_id is not None and body.client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Body client_id does not match the path",
        )
    if not body.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="text must not be empty"
        )
    if len(body.text) > settings.max_source_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"text exceeds {settings.max_source_chars} characters",
        )

    metadata = body.metadata.model_dump(mode="json")
    metadata[METADATA_IDEMPOTENCY_KEY] = body.idempotency_key

    job_id = await service.ingest_source(client_id, body.text, metadata)
    return SourceUploadResponse(
        job_id=job_id, client_id=client_id, status=IngestionStatus.QUEUED
    )


@router.get(
    "/ingestion-jobs/{job_id}",
    response_model=IngestionJobResponse,
    summary="Check ingestion status",
)
async def get_ingestion_job(
    job_id: str,
    client_id: str = Depends(require_client_access),
    service: RetrievalService = Depends(get_retrieval_service),
) -> IngestionJobResponse:
    job = await service.get_ingestion_status(client_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found"
        )
    return IngestionJobResponse(job_id=job.job_id, status=job.status, stage=job.stage)
