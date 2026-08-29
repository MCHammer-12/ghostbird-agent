from typing import Any

from app.config import Settings
from app.integrations.base import IntegrationError, request_json


class CRMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def upsert_hubspot_contact(
        self,
        email: str,
        firstname: str | None = None,
        lastname: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        props: dict[str, Any] = {"email": email}
        if firstname:
            props["firstname"] = firstname
        if lastname:
            props["lastname"] = lastname
        if properties:
            props.update(properties)

        data = await request_json(
            "POST",
            "https://api.hubapi.com/crm/v3/objects/contacts",
            service="hubspot",
            headers={
                "Authorization": f"Bearer {self.settings.hubspot_api_key}",
                "Content-Type": "application/json",
            },
            json={"properties": props},
        )
        return {"id": data.get("id"), "email": email}

    async def create_pipedrive_person(self, name: str, email: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name}
        if email:
            payload["email"] = [{"value": email, "primary": True}]

        data = await request_json(
            "POST",
            "https://api.pipedrive.com/v1/persons",
            service="pipedrive",
            json={**payload, "api_token": self.settings.pipedrive_api_token},
        )
        person = data.get("data", {})
        return {"id": person.get("id"), "name": name}
