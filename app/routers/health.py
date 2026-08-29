from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.dependencies.db import get_repository
from app.db.protocol import Repository

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "environment": settings.environment}


@router.get("/health/integrations")
def integration_status() -> dict[str, list[str] | str]:
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "configured": settings.configured_integrations(),
    }


@router.get("/healthz")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readiness(
    settings: Settings = Depends(get_settings),
    repo: Repository = Depends(get_repository),
) -> dict[str, str | bool]:
    database = "supabase" if settings.supabase_configured() else "memory"
    ready = await repo.ping()
    return {
        "status": "ready" if ready else "degraded",
        "environment": settings.environment,
        "database": database,
        "database_ready": ready,
    }
