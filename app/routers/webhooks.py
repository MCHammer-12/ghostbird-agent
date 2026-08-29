import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import get_settings
from app.dependencies.auth import verify_generic_webhook, verify_stripe_webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(payload: bytes = Depends(verify_stripe_webhook)) -> dict[str, Any]:
    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe event payload") from exc

    event_type = event.get("type", "unknown")
    # Extend with handlers per event type as needed.
    handlers: dict[str, str] = {
        "checkout.session.completed": "payment_completed",
        "customer.subscription.created": "subscription_created",
        "invoice.paid": "invoice_paid",
    }
    action = handlers.get(event_type, "unhandled")

    return {
        "received": True,
        "event_type": event_type,
        "action": action,
        "event_id": event.get("id"),
        "livemode": event.get("livemode"),
    }


@router.post("/generic/{name}")
async def generic_webhook(
    name: str,
    request: Request,
    _: None = Depends(verify_generic_webhook),
) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        payload = {"raw": (await request.body()).decode("utf-8", errors="replace")}

    return {
        "received": True,
        "name": name,
        "payload": payload,
    }
