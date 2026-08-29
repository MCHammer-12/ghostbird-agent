from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.dependencies.auth import require_client_access
from app.dependencies.ghostbird import get_ghostbird_service
from app.ghostbird.models import (
    DraftedPost,
    DraftInput,
    EnrichedPost,
    EnrichmentInput,
    IdeationInput,
    IdeationResult,
)
from app.ghostbird.service import GhostbirdService
from app.schemas.ghostbird import VoiceProfileResponse


router = APIRouter(
    prefix="/v1/clients/{client_id}",
    tags=["ghostbird"],
)


def _require_llm() -> None:
    if not get_settings().llm_configured():
        raise HTTPException(status_code=503, detail="LLM provider key not configured")


@router.get("/voice-profile", response_model=VoiceProfileResponse)
async def get_voice_profile(
    client_id: str = Depends(require_client_access),
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> VoiceProfileResponse:
    profile = await service.repository.get_voice_profile(client_id)
    return VoiceProfileResponse(profile=profile)


@router.post("/posts:enrich", response_model=EnrichedPost)
async def enrich_post(
    body: EnrichmentInput,
    client_id: str = Depends(require_client_access),
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> EnrichedPost:
    _require_llm()
    return await service.enrich(client_id, body)


@router.post("/posts:ideate", response_model=IdeationResult)
async def ideate_posts(
    body: IdeationInput,
    client_id: str = Depends(require_client_access),
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> IdeationResult:
    _require_llm()
    return await service.ideate(client_id, body)


@router.post("/posts:draft", response_model=DraftedPost)
async def draft_post(
    body: DraftInput,
    client_id: str = Depends(require_client_access),
    service: GhostbirdService = Depends(get_ghostbird_service),
) -> DraftedPost:
    _require_llm()
    return await service.draft(client_id, body)
