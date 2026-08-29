from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies.ghostbird import get_ghostbird_service
from app.ghostbird.models import (
    EnrichedPost,
    EnrichmentInput,
    IdeationInput,
    IdeationResult,
    StoredEvidence,
)
from app.ghostbird.service import GhostbirdService


router = APIRouter(prefix="/demo/v1/clients/{client_id}", tags=["local-demo"])


def require_local_demo(
    request: Request,
) -> None:
    host = request.client.host if request.client else ""
    if host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/posts:enrich", response_model=EnrichedPost)
async def demo_enrich_post(
    client_id: str,
    body: EnrichmentInput,
    _: None = Depends(require_local_demo),
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> EnrichedPost:
    return await service.enrich(client_id, body, verify_output=False)


@router.post("/posts:ideate", response_model=IdeationResult)
async def demo_ideate_posts(
    client_id: str,
    body: IdeationInput,
    _: None = Depends(require_local_demo),
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> IdeationResult:
    return await service.ideate(client_id, body, verify_output=False)


@router.get("/evidence/{evidence_id}", response_model=StoredEvidence)
async def demo_get_evidence(
    client_id: str,
    evidence_id: str,
    _: None = Depends(require_local_demo),
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> StoredEvidence:
    record = await service.repository.get_evidence(client_id, evidence_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return record
