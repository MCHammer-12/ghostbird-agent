"""Request and response models for the Ghostbird CRUD API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    name: str = Field(min_length=1)
    summary: str | None = None
    writing_style: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    summary: str | None = None
    writing_style: str | None = None


class Client(BaseModel):
    id: str
    name: str
    summary: str | None = None
    writing_style: str | None = None
    inserted_at: datetime
    updated_at: datetime


class UploadCreate(BaseModel):
    text: str = Field(min_length=1)
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class UploadUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1)
    summary: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None


class Upload(BaseModel):
    id: str
    client_id: str
    text: str
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    inserted_at: datetime
    updated_at: datetime


class TagCreate(BaseModel):
    name: str = Field(min_length=1)


class TagUpdate(BaseModel):
    name: str = Field(min_length=1)


class Tag(BaseModel):
    id: str
    client_id: str
    name: str
    inserted_at: datetime
    updated_at: datetime


class UploadTagsReplace(BaseModel):
    tag_ids: list[str] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str | None = None
