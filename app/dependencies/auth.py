from fastapi import Depends, Header, HTTPException, Request

from app.config import Settings, get_settings


def verify_api_key(
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if not settings.api_key:
        raise HTTPException(status_code=503, detail="API_KEY not configured")
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def verify_generic_webhook(
    settings: Settings = Depends(get_settings),
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> None:
    if not settings.webhook_secret:
        raise HTTPException(status_code=503, detail="WEBHOOK_SECRET not configured")
    if x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


async def verify_stripe_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> bytes:
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="STRIPE_WEBHOOK_SECRET not configured")

    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        import stripe

        stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Stripe integration not installed") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature") from exc

    return payload


def require_client_access(
    client_id: str,
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """Authenticate the caller, then authorize the requested client.

    This runs before any retrieval call, in code, never in a prompt
    (docs/TRACKS.md, Track 2 Security Rule). Returns the client_id so routers
    depend on the *authorized* value rather than the raw path parameter.
    """
    if not settings.api_keys and not settings.api_key:
        raise HTTPException(status_code=503, detail="API_KEY or API_KEYS not configured")

    allowed = settings.client_ids_for_key(x_api_key or "")
    if allowed is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # An empty allow-list means every client (the single-API_KEY dev fallback).
    if allowed and client_id not in allowed:
        raise HTTPException(
            status_code=403, detail="API key is not authorized for this client"
        )
    return client_id
