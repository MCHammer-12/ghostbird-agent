from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, status

from app.config import Settings, get_settings
from app.db.memory import MemoryRepository
from app.db.protocol import Repository
from app.db.supabase_repo import SupabaseRepository


@lru_cache
def _build_repository(use_supabase: bool) -> Repository:
    settings = get_settings()
    if use_supabase:
        return SupabaseRepository(settings)
    return MemoryRepository()


def get_repository(settings: Settings = Depends(get_settings)) -> Repository:
    if settings.supabase_configured():
        return _build_repository(True)
    if settings.environment == "development":
        return _build_repository(False)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured",
    )


def clear_repository_cache() -> None:
    _build_repository.cache_clear()
