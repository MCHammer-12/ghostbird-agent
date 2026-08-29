from fastapi import APIRouter

from app.config import get_settings

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
