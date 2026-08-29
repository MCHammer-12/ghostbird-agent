"""Review a partial draft against the client's evidence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.dependencies.auth import require_client_access
from app.dependencies.services import get_llm_client, get_retrieval_service
from app.generation.drafts import review_draft
from app.integrations.llm import LLMClient
from app.schemas.api import DraftReviewRequest
from app.schemas.shared import DraftReviewResponse
from app.services.protocol import RetrievalService
from app.services.retrieval import retrieve_scoped

router = APIRouter(prefix="/v1/clients/{client_id}", tags=["drafts"])


@router.post(
    "/drafts:review",
    response_model=DraftReviewResponse,
    summary="Review a draft against client evidence",
)
async def review_client_draft(
    body: DraftReviewRequest,
    client_id: str = Depends(require_client_access),
    settings: Settings = Depends(get_settings),
    service: RetrievalService = Depends(get_retrieval_service),
    llm: LLMClient = Depends(get_llm_client),
) -> DraftReviewResponse:
    if not body.draft_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="draft_text must not be empty"
        )
    if len(body.draft_text) > settings.max_draft_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"draft_text exceeds {settings.max_draft_chars} characters",
        )

    cards = await retrieve_scoped(service, settings, client_id, body.draft_text)
    return await review_draft(llm, settings, body.draft_text, cards)
