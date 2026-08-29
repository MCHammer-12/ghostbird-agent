from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.dependencies.auth import verify_api_key
from app.dependencies.ghostbird import get_ghostbird_service
from app.ghostbird.models import (
    EnrichedPost,
    EnrichmentInput,
    DraftedPost,
    DraftInput,
    IdeationInput,
    IdeationResult,
    IngestionResult,
    SourceDocument,
    StoredEvidence,
)
from app.ghostbird.service import GhostbirdService
from app.integrations.base import IntegrationError
from app.schemas.ghostbird import (
    EvidenceSearchRequest,
    EvidenceSearchResponse,
    SourceUploadRequest,
    VoiceProfileResponse,
)


router = APIRouter(
    prefix="/v1/clients/{client_id}",
    tags=["ghostbird"],
    dependencies=[Depends(verify_api_key)],
)


def _require_llm() -> None:
    if not get_settings().llm_configured():
        raise HTTPException(status_code=503, detail="LLM provider key not configured")


def _integration_error(exc: IntegrationError) -> HTTPException:
    return HTTPException(status_code=502, detail={"service": exc.service, "message": exc.message})


@router.post("/sources", response_model=IngestionResult)
async def ingest_source(
    client_id: str,
    body: SourceUploadRequest,
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> IngestionResult:
    _require_llm()
    source = SourceDocument(client_id=client_id, **body.model_dump())
    try:
        return await service.ingest(source)
    except IntegrationError as exc:
        raise _integration_error(exc) from exc


@router.post("/search", response_model=EvidenceSearchResponse)
async def search_evidence(
    client_id: str,
    body: EvidenceSearchRequest,
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> EvidenceSearchResponse:
    evidence = await service.repository.search_evidence(client_id, body.query, body.top_k)
    return EvidenceSearchResponse(evidence=evidence)


@router.get("/evidence/{evidence_id}", response_model=StoredEvidence)
async def get_evidence(
    client_id: str,
    evidence_id: str,
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> StoredEvidence:
    evidence = await service.repository.get_evidence(client_id, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence


@router.get("/voice-profile", response_model=VoiceProfileResponse)
async def get_voice_profile(
    client_id: str,
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> VoiceProfileResponse:
    profile = await service.repository.get_voice_profile(client_id)
    return VoiceProfileResponse(profile=profile)


@router.post("/posts:enrich", response_model=EnrichedPost)
async def enrich_post(
    client_id: str,
    body: EnrichmentInput,
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> EnrichedPost:
    _require_llm()
    try:
        return await service.enrich(client_id, body)
    except IntegrationError as exc:
        raise _integration_error(exc) from exc


@router.post("/posts:ideate", response_model=IdeationResult)
async def ideate_posts(
    client_id: str,
    body: IdeationInput,
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> IdeationResult:
    _require_llm()
    try:
        return await service.ideate(client_id, body)
    except IntegrationError as exc:
        raise _integration_error(exc) from exc


@router.post("/posts:draft", response_model=DraftedPost)
async def draft_post(
    client_id: str,
    body: DraftInput,
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> DraftedPost:
    _require_llm()
    try:
        return await service.draft(client_id, body)
    except IntegrationError as exc:
        raise _integration_error(exc) from exc
