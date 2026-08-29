from typing import Any

from app.config import Settings
from app.integrations.base import IntegrationError, request_json


class ApifyClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def run_actor(self, actor_id: str, input_data: dict[str, Any] | None = None) -> dict[str, Any]:
        data = await request_json(
            "POST",
            f"https://api.apify.com/v2/acts/{actor_id}/runs",
            service="apify",
            headers={"Authorization": f"Bearer {self.settings.apify_api_token}"},
            json=input_data or {},
            timeout=60.0,
        )
        run = data.get("data", {})
        run_id = run.get("id")
        if not run_id:
            raise IntegrationError("apify", "Missing run id in response")
        return {
            "run_id": run_id,
            "status": run.get("status"),
            "dataset_url": f"https://api.apify.com/v2/datasets/{run.get('defaultDatasetId')}/items",
        }
