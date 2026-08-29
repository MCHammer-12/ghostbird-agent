import asyncio
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
        query = self._client().table(table).select(select).limit(limit)
        result = await asyncio.to_thread(query.execute)
        return result.data or []

    async def insert(self, table: str, row: dict[str, Any]) -> list[dict[str, Any]]:
        query = self._client().table(table).insert(row)
        result = await asyncio.to_thread(query.execute)
        return result.data or []

    async def select(
        self,
        table: str,
        select: str = "*",
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        query = self._client().table(table).select(select)
        for column, value in (filters or {}).items():
            query = query.eq(column, value)
        result = await asyncio.to_thread(query.limit(limit).execute)
        return result.data or []

    async def upsert(
        self,
        table: str,
        rows: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self._client().table(table).upsert(rows, on_conflict=on_conflict)
        result = await asyncio.to_thread(query.execute)
        return result.data or []

    async def update(
        self,
        table: str,
        values: dict[str, Any],
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        query = self._client().table(table).update(values)
        for column, value in filters.items():
            query = query.eq(column, value)
        result = await asyncio.to_thread(query.execute)
        return result.data or []

    async def rpc(self, function: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        query = self._client().rpc(function, params)
        result = await asyncio.to_thread(query.execute)
        if isinstance(result.data, list):
            return result.data
        return [result.data] if result.data else []
