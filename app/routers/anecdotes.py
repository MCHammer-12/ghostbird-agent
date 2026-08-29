"""Find an anecdote grounded in the client's own evidence."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.dependencies.auth import require_client_access
from app.dependencies.services import get_llm_client, get_retrieval_service
from app.generation.anecdotes import find_anecdotes
from app.integrations.llm import LLMClient
from app.schemas.api import AnecdoteSearchRequest, AnecdoteSearchResponse
from app.services.protocol import RetrievalService
from app.services.retrieval import retrieve_scoped

router = APIRouter(prefix="/v1/clients/{client_id}", tags=["anecdotes"])


@router.post(
    "/anecdotes:search",
    response_model=AnecdoteSearchResponse,
    summary="Find an anecdote for a post theme",
)
async def search_anecdotes(
    body: AnecdoteSearchRequest,
    client_id: str = Depends(require_client_access),
    settings: Settings = Depends(get_settings),
    service: RetrievalService = Depends(get_retrieval_service),
    llm: LLMClient = Depends(get_llm_client),
) -> AnecdoteSearchResponse:
    cards = await retrieve_scoped(service, settings, client_id, body.theme)
    return await find_anecdotes(llm, settings, body.theme, cards)
