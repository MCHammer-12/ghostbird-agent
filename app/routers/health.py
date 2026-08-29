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


@router.get("/healthz")
def liveness() -> dict[str, str]:
    """The application is running."""
    return {"status": "ok"}


@router.get("/readyz")
def readiness() -> dict[str, str]:
    """Required dependencies are available."""
    settings = get_settings()
    return {
        "status": "ready",
        "environment": settings.environment,
        "retrieval_backend": settings.retrieval_backend.value,
    }
