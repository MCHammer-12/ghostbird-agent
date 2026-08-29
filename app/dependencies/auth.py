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
