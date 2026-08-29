"""In-memory repository for tests and local dev without Supabase."""

from __future__ import annotations

import itertools
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.db.errors import ConflictError, NotFoundError
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


def _now() -> datetime:
    return datetime.now(UTC)


class MemoryRepository:
    def __init__(self) -> None:
        self._clients: dict[str, dict[str, Any]] = {}
        self._uploads: dict[str, dict[str, Any]] = {}
        self._tags: dict[str, dict[str, Any]] = {}
        self._upload_tags: set[tuple[str, str]] = set()
        self._ids = itertools.count(1)

    def _next(self, prefix: str) -> str:
        return f"{prefix}_{next(self._ids):03d}"

    def _require_client(self, client_id: str) -> dict[str, Any]:
        client = self._clients.get(client_id)
        if client is None:
            raise NotFoundError(f"Client {client_id} not found")
        return client

    def _require_upload(self, client_id: str, upload_id: str) -> dict[str, Any]:
        self._require_client(client_id)
        upload = self._uploads.get(upload_id)
        if upload is None or upload["client_id"] != client_id:
            raise NotFoundError(f"Upload {upload_id} not found")
        return upload

    def _require_tag(self, client_id: str, tag_id: str) -> dict[str, Any]:
        self._require_client(client_id)
        tag = self._tags.get(tag_id)
        if tag is None or tag["client_id"] != client_id:
            raise NotFoundError(f"Tag {tag_id} not found")
        return tag

    async def list_clients(self, q: str | None = None) -> list[Client]:
        rows = sorted(self._clients.values(), key=lambda row: row["name"].lower())
        if q:
            needle = q.lower()
            rows = [row for row in rows if needle in row["name"].lower()]
        return [Client.model_validate(row) for row in rows]

    async def create_client(self, data: ClientCreate) -> Client:
        now = _now()
        row = {
            "id": self._next("cli"),
            "name": data.name,
            "summary": data.summary,
            "writing_style": data.writing_style,
            "inserted_at": now,
            "updated_at": now,
        }
        self._clients[row["id"]] = row
        return Client.model_validate(row)

    async def get_client(self, client_id: str) -> Client:
        return Client.model_validate(self._require_client(client_id))

    async def update_client(self, client_id: str, data: ClientUpdate) -> Client:
        row = self._require_client(client_id)
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return Client.model_validate(row)
        row.update(updates)
        row["updated_at"] = _now()
        return Client.model_validate(row)

    async def delete_client(self, client_id: str) -> None:
        self._require_client(client_id)
        upload_ids = [
            upload_id
            for upload_id, upload in self._uploads.items()
            if upload["client_id"] == client_id
        ]
        tag_ids = [
            tag_id for tag_id, tag in self._tags.items() if tag["client_id"] == client_id
        ]
        for upload_id in upload_ids:
            self._upload_tags = {
                pair for pair in self._upload_tags if pair[0] != upload_id
            }
            del self._uploads[upload_id]
        for tag_id in tag_ids:
            self._upload_tags = {
                pair for pair in self._upload_tags if pair[1] != tag_id
            }
            del self._tags[tag_id]
        del self._clients[client_id]

    async def list_uploads(
        self, client_id: str, tag_id: str | None = None
    ) -> list[Upload]:
        self._require_client(client_id)
        rows = [
            upload
            for upload in self._uploads.values()
            if upload["client_id"] == client_id
        ]
        if tag_id is not None:
            self._require_tag(client_id, tag_id)
            allowed = {
                upload_id
                for upload_id, linked_tag_id in self._upload_tags
                if linked_tag_id == tag_id
            }
            rows = [row for row in rows if row["id"] in allowed]
        rows.sort(key=lambda row: row["created_at"], reverse=True)
        return [Upload.model_validate(row) for row in rows]

    async def create_upload(self, client_id: str, data: UploadCreate) -> Upload:
        self._require_client(client_id)
        now = _now()
        row = {
            "id": self._next("upl"),
            "client_id": client_id,
            "text": data.text,
            "summary": data.summary,
            "metadata": deepcopy(data.metadata),
            "created_at": data.created_at or now,
            "inserted_at": now,
            "updated_at": now,
        }
        self._uploads[row["id"]] = row
        return Upload.model_validate(row)

    async def get_upload(self, client_id: str, upload_id: str) -> Upload:
        return Upload.model_validate(self._require_upload(client_id, upload_id))

    async def update_upload(
        self, client_id: str, upload_id: str, data: UploadUpdate
    ) -> Upload:
        row = self._require_upload(client_id, upload_id)
        updates = data.model_dump(exclude_unset=True)
        if "metadata" in updates and updates["metadata"] is not None:
            updates["metadata"] = deepcopy(updates["metadata"])
        if updates:
            row.update(updates)
            row["updated_at"] = _now()
        return Upload.model_validate(row)

    async def delete_upload(self, client_id: str, upload_id: str) -> None:
        self._require_upload(client_id, upload_id)
        self._upload_tags = {
            pair for pair in self._upload_tags if pair[0] != upload_id
        }
        del self._uploads[upload_id]

    async def list_tags(self, client_id: str) -> list[Tag]:
        self._require_client(client_id)
        rows = [
            tag for tag in self._tags.values() if tag["client_id"] == client_id
        ]
        rows.sort(key=lambda row: row["name"].lower())
        return [Tag.model_validate(row) for row in rows]

    async def create_tag(self, client_id: str, data: TagCreate) -> Tag:
        self._require_client(client_id)
        for tag in self._tags.values():
            if tag["client_id"] == client_id and tag["name"] == data.name:
                raise ConflictError(f"Tag {data.name!r} already exists for client")
        now = _now()
        row = {
            "id": self._next("tag"),
            "client_id": client_id,
            "name": data.name,
            "inserted_at": now,
            "updated_at": now,
        }
        self._tags[row["id"]] = row
        return Tag.model_validate(row)

    async def get_tag(self, client_id: str, tag_id: str) -> Tag:
        return Tag.model_validate(self._require_tag(client_id, tag_id))

    async def update_tag(
        self, client_id: str, tag_id: str, data: TagUpdate
    ) -> Tag:
        row = self._require_tag(client_id, tag_id)
        for tag in self._tags.values():
            if (
                tag["client_id"] == client_id
                and tag["name"] == data.name
                and tag["id"] != tag_id
            ):
                raise ConflictError(f"Tag {data.name!r} already exists for client")
        row["name"] = data.name
        row["updated_at"] = _now()
        return Tag.model_validate(row)

    async def delete_tag(self, client_id: str, tag_id: str) -> None:
        self._require_tag(client_id, tag_id)
        self._upload_tags = {
            pair for pair in self._upload_tags if pair[1] != tag_id
        }
        del self._tags[tag_id]

    async def list_upload_tags(self, client_id: str, upload_id: str) -> list[Tag]:
        self._require_upload(client_id, upload_id)
        tag_ids = [
            tag_id
            for linked_upload_id, tag_id in self._upload_tags
            if linked_upload_id == upload_id
        ]
        tags = [self._tags[tag_id] for tag_id in tag_ids if tag_id in self._tags]
        tags.sort(key=lambda row: row["name"].lower())
        return [Tag.model_validate(row) for row in tags]

    async def replace_upload_tags(
        self, client_id: str, upload_id: str, tag_ids: list[str]
    ) -> list[Tag]:
        self._require_upload(client_id, upload_id)
        seen: set[str] = set()
        for tag_id in tag_ids:
            if tag_id in seen:
                raise ConflictError("Duplicate tag_ids are not allowed")
            seen.add(tag_id)
            self._require_tag(client_id, tag_id)
        self._upload_tags = {
            pair
            for pair in self._upload_tags
            if pair[0] != upload_id
        }
        for tag_id in tag_ids:
            self._upload_tags.add((upload_id, tag_id))
        return await self.list_upload_tags(client_id, upload_id)

    async def attach_upload_tag(
        self, client_id: str, upload_id: str, tag_id: str
    ) -> None:
        self._require_upload(client_id, upload_id)
        self._require_tag(client_id, tag_id)
        self._upload_tags.add((upload_id, tag_id))

    async def detach_upload_tag(
        self, client_id: str, upload_id: str, tag_id: str
    ) -> None:
        self._require_upload(client_id, upload_id)
        self._require_tag(client_id, tag_id)
        pair = (upload_id, tag_id)
        if pair not in self._upload_tags:
            raise NotFoundError("Tag is not attached to this upload")
        self._upload_tags.remove(pair)

    async def ping(self) -> bool:
        return True
