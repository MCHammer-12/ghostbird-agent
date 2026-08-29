"""Client-scoped evidence search. Returns evidence only; generates nothing."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.dependencies.auth import require_client_access
from app.dependencies.services import get_retrieval_service
from app.schemas.api import SearchRequest, SearchResponse
from app.services.protocol import RetrievalService
from app.services.retrieval import retrieve_scoped

router = APIRouter(prefix="/v1/clients/{client_id}", tags=["search"])


@router.post("/search", response_model=SearchResponse, summary="Search client evidence")
async def search_evidence(
    body: SearchRequest,
    client_id: str = Depends(require_client_access),
    settings: Settings = Depends(get_settings),
    service: RetrievalService = Depends(get_retrieval_service),
) -> SearchResponse:
    cards = await retrieve_scoped(
        service, settings, client_id, body.query, body.filters, body.top_k
    )
    return SearchResponse(evidence=cards)
