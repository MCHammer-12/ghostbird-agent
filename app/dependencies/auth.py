from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings


def verify_api_key(
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if not settings.api_key:
        raise HTTPException(status_code=503, detail="API_KEY not configured")
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def require_client_access(
    client_id: str,
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """Authenticate the caller, then authorize the requested client."""
    if not settings.api_keys and not settings.api_key:
        raise HTTPException(status_code=503, detail="API_KEY or API_KEYS not configured")

    allowed = settings.client_ids_for_key(x_api_key or "")
    if allowed is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if allowed and client_id not in allowed:
        raise HTTPException(
            status_code=403, detail="API key is not authorized for this client"
        )
    return client_id
