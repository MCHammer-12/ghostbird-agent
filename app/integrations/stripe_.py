from typing import Any

from app.config import Settings
from app.integrations.base import IntegrationError


class StripeClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _stripe(self):
        try:
            import stripe
        except ImportError as exc:
            raise IntegrationError("stripe", "Install with: uv sync --extra stripe") from exc

        stripe.api_key = self.settings.stripe_secret_key
        return stripe

    async def create_customer(self, email: str, name: str | None = None, metadata: dict | None = None) -> dict[str, Any]:
        stripe = self._stripe()
        customer = stripe.Customer.create(email=email, name=name, metadata=metadata or {})
        return {"id": customer.id, "email": customer.email}
