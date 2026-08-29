"""Supabase-backed repository."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, TypeVar

from app.config import Settings
from app.db.errors import ConflictError, DatabaseError, NotFoundError
from app.schemas.entities import (
    Client,
    ClientCreate,
    ClientUpdate,
    Tag,
    TagCreate,
    TagUpdate,
    Upload,
    UploadCreate,
    UploadUpdate,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class SupabaseRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _client(self):
        try:
            from supabase import create_client
        except ImportError as exc:
            raise DatabaseError(
                "Install supabase: uv sync --extra supabase"
            ) from exc
        return create_client(
            self._settings.supabase_url,
            self._settings.supabase_service_role_key,
        )

    async def _run(self, fn: Callable[[], T]) -> T:
        return await asyncio.to_thread(fn)

    def _map_db_error(self, exc: Exception) -> Exception:
        message = str(exc)
        if "23505" in message or "duplicate key" in message.lower():
            return ConflictError("Resource already exists")
        if "PGRST116" in message or "0 rows" in message:
            return NotFoundError("Resource not found")
        logger.error("supabase error: %s", type(exc).__name__)
        return DatabaseError("Database request failed")

    async def list_clients(self, q: str | None = None) -> list[Client]:
        def _query() -> list[Client]:
            query = self._client().table("clients").select("*").order("name")
            if q:
                query = query.ilike("name", f"%{q}%")
            result = query.execute()
            return [Client.model_validate(row) for row in result.data or []]

        try:
            return await self._run(_query)
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def create_client(self, data: ClientCreate) -> Client:
        payload = data.model_dump()

        def _insert() -> Client:
            result = self._client().table("clients").insert(payload).execute()
            if not result.data:
                raise DatabaseError("Failed to create client")
            return Client.model_validate(result.data[0])

        try:
            return await self._run(_insert)
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def get_client(self, client_id: str) -> Client:
        def _get() -> Client:
            result = (
                self._client()
                .table("clients")
                .select("*")
                .eq("id", client_id)
                .maybe_single()
                .execute()
            )
            if not result.data:
                raise NotFoundError(f"Client {client_id} not found")
            return Client.model_validate(result.data)

        try:
            return await self._run(_get)
        except NotFoundError:
            raise
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def update_client(self, client_id: str, data: ClientUpdate) -> Client:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return await self.get_client(client_id)

        def _update() -> Client:
            result = (
                self._client()
                .table("clients")
                .update(updates)
                .eq("id", client_id)
                .execute()
            )
            if not result.data:
                raise NotFoundError(f"Client {client_id} not found")
            return Client.model_validate(result.data[0])

        try:
            return await self._run(_update)
        except NotFoundError:
            raise
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def delete_client(self, client_id: str) -> None:
        await self.get_client(client_id)

        def _delete() -> None:
            self._client().table("clients").delete().eq("id", client_id).execute()

        try:
            await self._run(_delete)
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def list_uploads(
        self, client_id: str, tag_id: str | None = None
    ) -> list[Upload]:
        await self.get_client(client_id)
        if tag_id is not None:
            await self.get_tag(client_id, tag_id)

        def _query() -> list[Upload]:
            if tag_id is None:
                result = (
                    self._client()
                    .table("uploads")
                    .select("*")
                    .eq("client_id", client_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                return [Upload.model_validate(row) for row in result.data or []]

            links = (
                self._client()
                .table("uploads__tags")
                .select("upload_id")
                .eq("tag_id", tag_id)
                .execute()
            )
            upload_ids = [row["upload_id"] for row in links.data or []]
            if not upload_ids:
                return []
            result = (
                self._client()
                .table("uploads")
                .select("*")
                .eq("client_id", client_id)
                .in_("id", upload_ids)
                .order("created_at", desc=True)
                .execute()
            )
            return [Upload.model_validate(row) for row in result.data or []]

        try:
            return await self._run(_query)
        except NotFoundError:
            raise
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def create_upload(self, client_id: str, data: UploadCreate) -> Upload:
        await self.get_client(client_id)
        payload: dict[str, Any] = {
            "client_id": client_id,
            "text": data.text,
            "summary": data.summary,
            "metadata": data.metadata,
        }
        if data.created_at is not None:
            payload["created_at"] = data.created_at.isoformat()

        def _insert() -> Upload:
            result = self._client().table("uploads").insert(payload).execute()
            if not result.data:
                raise DatabaseError("Failed to create upload")
            return Upload.model_validate(result.data[0])

        try:
            return await self._run(_insert)
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def get_upload(self, client_id: str, upload_id: str) -> Upload:
        def _get() -> Upload:
            result = (
                self._client()
                .table("uploads")
                .select("*")
                .eq("id", upload_id)
                .eq("client_id", client_id)
                .maybe_single()
                .execute()
            )
            if not result.data:
                raise NotFoundError(f"Upload {upload_id} not found")
            return Upload.model_validate(result.data)

        try:
            return await self._run(_get)
        except NotFoundError:
            raise
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def update_upload(
        self, client_id: str, upload_id: str, data: UploadUpdate
    ) -> Upload:
        updates = data.model_dump(exclude_unset=True)
        if "created_at" in updates and updates["created_at"] is not None:
            updates["created_at"] = updates["created_at"].isoformat()
        if not updates:
            return await self.get_upload(client_id, upload_id)

        def _update() -> Upload:
            result = (
                self._client()
                .table("uploads")
                .update(updates)
                .eq("id", upload_id)
                .eq("client_id", client_id)
                .execute()
            )
            if not result.data:
                raise NotFoundError(f"Upload {upload_id} not found")
            return Upload.model_validate(result.data[0])

        try:
            return await self._run(_update)
        except NotFoundError:
            raise
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def delete_upload(self, client_id: str, upload_id: str) -> None:
        await self.get_upload(client_id, upload_id)

        def _delete() -> None:
            (
                self._client()
                .table("uploads")
                .delete()
                .eq("id", upload_id)
                .eq("client_id", client_id)
                .execute()
            )

        try:
            await self._run(_delete)
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def list_tags(self, client_id: str) -> list[Tag]:
        await self.get_client(client_id)

        def _query() -> list[Tag]:
            result = (
                self._client()
                .table("tags")
                .select("*")
                .eq("client_id", client_id)
                .order("name")
                .execute()
            )
            return [Tag.model_validate(row) for row in result.data or []]

        try:
            return await self._run(_query)
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def create_tag(self, client_id: str, data: TagCreate) -> Tag:
        await self.get_client(client_id)
        payload = {"client_id": client_id, "name": data.name}

        def _insert() -> Tag:
            result = self._client().table("tags").insert(payload).execute()
            if not result.data:
                raise DatabaseError("Failed to create tag")
            return Tag.model_validate(result.data[0])

        try:
            return await self._run(_insert)
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def get_tag(self, client_id: str, tag_id: str) -> Tag:
        def _get() -> Tag:
            result = (
                self._client()
                .table("tags")
                .select("*")
                .eq("id", tag_id)
                .eq("client_id", client_id)
                .maybe_single()
                .execute()
            )
            if not result.data:
                raise NotFoundError(f"Tag {tag_id} not found")
            return Tag.model_validate(result.data)

        try:
            return await self._run(_get)
        except NotFoundError:
            raise
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def update_tag(
        self, client_id: str, tag_id: str, data: TagUpdate
    ) -> Tag:
        def _update() -> Tag:
            result = (
                self._client()
                .table("tags")
                .update({"name": data.name})
                .eq("id", tag_id)
                .eq("client_id", client_id)
                .execute()
            )
            if not result.data:
                raise NotFoundError(f"Tag {tag_id} not found")
            return Tag.model_validate(result.data[0])

        try:
            return await self._run(_update)
        except NotFoundError:
            raise
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def delete_tag(self, client_id: str, tag_id: str) -> None:
        await self.get_tag(client_id, tag_id)

        def _delete() -> None:
            (
                self._client()
                .table("tags")
                .delete()
                .eq("id", tag_id)
                .eq("client_id", client_id)
                .execute()
            )

        try:
            await self._run(_delete)
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def list_upload_tags(self, client_id: str, upload_id: str) -> list[Tag]:
        await self.get_upload(client_id, upload_id)

        def _query() -> list[Tag]:
            links = (
                self._client()
                .table("uploads__tags")
                .select("tag_id")
                .eq("upload_id", upload_id)
                .execute()
            )
            tag_ids = [row["tag_id"] for row in links.data or []]
            if not tag_ids:
                return []
            result = (
                self._client()
                .table("tags")
                .select("*")
                .eq("client_id", client_id)
                .in_("id", tag_ids)
                .order("name")
                .execute()
            )
            return [Tag.model_validate(row) for row in result.data or []]

        try:
            return await self._run(_query)
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def replace_upload_tags(
        self, client_id: str, upload_id: str, tag_ids: list[str]
    ) -> list[Tag]:
        await self.get_upload(client_id, upload_id)
        seen: set[str] = set()
        for tag_id in tag_ids:
            if tag_id in seen:
                raise ConflictError("Duplicate tag_ids are not allowed")
            seen.add(tag_id)
            await self.get_tag(client_id, tag_id)

        def _replace() -> list[Tag]:
            client = self._client()
            client.table("uploads__tags").delete().eq("upload_id", upload_id).execute()
            if tag_ids:
                rows = [{"upload_id": upload_id, "tag_id": tag_id} for tag_id in tag_ids]
                client.table("uploads__tags").insert(rows).execute()
            if not tag_ids:
                return []
            result = (
                client.table("tags")
                .select("*")
                .eq("client_id", client_id)
                .in_("id", tag_ids)
                .order("name")
                .execute()
            )
            return [Tag.model_validate(row) for row in result.data or []]

        try:
            return await self._run(_replace)
        except (ConflictError, NotFoundError):
            raise
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def attach_upload_tag(
        self, client_id: str, upload_id: str, tag_id: str
    ) -> None:
        await self.get_upload(client_id, upload_id)
        await self.get_tag(client_id, tag_id)

        def _attach() -> None:
            self._client().table("uploads__tags").insert(
                {"upload_id": upload_id, "tag_id": tag_id}
            ).execute()

        try:
            await self._run(_attach)
        except Exception as exc:
            mapped = self._map_db_error(exc)
            if isinstance(mapped, ConflictError):
                return
            raise mapped from exc

    async def detach_upload_tag(
        self, client_id: str, upload_id: str, tag_id: str
    ) -> None:
        await self.get_upload(client_id, upload_id)
        await self.get_tag(client_id, tag_id)

        def _detach() -> None:
            result = (
                self._client()
                .table("uploads__tags")
                .delete()
                .eq("upload_id", upload_id)
                .eq("tag_id", tag_id)
                .execute()
            )
            if not result.data:
                raise NotFoundError("Tag is not attached to this upload")

        try:
            await self._run(_detach)
        except NotFoundError:
            raise
        except Exception as exc:
            raise self._map_db_error(exc) from exc

    async def ping(self) -> bool:
        def _ping() -> bool:
            self._client().table("clients").select("id").limit(1).execute()
            return True

        try:
            return await self._run(_ping)
        except Exception as exc:
            logger.error("supabase ping failed: %s", type(exc).__name__)
            return False
