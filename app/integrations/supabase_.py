from typing import Any

from app.config import Settings
from app.integrations.base import IntegrationError


class SupabaseClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _client(self):
        try:
            from supabase import create_client
        except ImportError as exc:
            raise IntegrationError("supabase", "Install with: uv sync --extra supabase") from exc

        return create_client(self.settings.supabase_url, self.settings.supabase_service_role_key)

    async def query(self, table: str, select: str = "*", limit: int = 10) -> list[dict[str, Any]]:
        result = self._client().table(table).select(select).limit(limit).execute()
        return result.data or []

    async def insert(self, table: str, row: dict[str, Any]) -> list[dict[str, Any]]:
        result = self._client().table(table).insert(row).execute()
        return result.data or []
