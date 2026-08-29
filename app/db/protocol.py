from __future__ import annotations

from typing import Protocol

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


class Repository(Protocol):
    async def list_clients(self, q: str | None = None) -> list[Client]: ...

    async def create_client(self, data: ClientCreate) -> Client: ...

    async def get_client(self, client_id: str) -> Client: ...

    async def update_client(self, client_id: str, data: ClientUpdate) -> Client: ...

    async def delete_client(self, client_id: str) -> None: ...

    async def list_uploads(
        self, client_id: str, tag_id: str | None = None
    ) -> list[Upload]: ...

    async def create_upload(self, client_id: str, data: UploadCreate) -> Upload: ...

    async def get_upload(self, client_id: str, upload_id: str) -> Upload: ...

    async def update_upload(
        self, client_id: str, upload_id: str, data: UploadUpdate
    ) -> Upload: ...

    async def delete_upload(self, client_id: str, upload_id: str) -> None: ...

    async def list_tags(self, client_id: str) -> list[Tag]: ...

    async def create_tag(self, client_id: str, data: TagCreate) -> Tag: ...

    async def get_tag(self, client_id: str, tag_id: str) -> Tag: ...

    async def update_tag(
        self, client_id: str, tag_id: str, data: TagUpdate
    ) -> Tag: ...

    async def delete_tag(self, client_id: str, tag_id: str) -> None: ...

    async def list_upload_tags(self, client_id: str, upload_id: str) -> list[Tag]: ...

    async def replace_upload_tags(
        self, client_id: str, upload_id: str, tag_ids: list[str]
    ) -> list[Tag]: ...

    async def attach_upload_tag(
        self, client_id: str, upload_id: str, tag_id: str
    ) -> None: ...

    async def detach_upload_tag(
        self, client_id: str, upload_id: str, tag_id: str
    ) -> None: ...

    async def ping(self) -> bool: ...
