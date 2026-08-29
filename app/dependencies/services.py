"""Binds the Track 1 contract to an implementation at startup."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from app.config import RetrievalBackend, Settings, get_settings
from app.integrations.llm import LLMClient
from app.services.mock import MockRetrievalService
from app.services.protocol import RetrievalService
from app.services.track1 import Track1RetrievalService


@lru_cache
def _build_retrieval_service(backend: RetrievalBackend) -> RetrievalService:
    settings = get_settings()
    match backend:
        case RetrievalBackend.TRACK1:
            return Track1RetrievalService()
        case _:
            return MockRetrievalService(settings)


def get_retrieval_service(
    settings: Settings = Depends(get_settings),
) -> RetrievalService:
    return _build_retrieval_service(settings.retrieval_backend)


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    return LLMClient(settings)
