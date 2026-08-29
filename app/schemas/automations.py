from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMCompleteRequest(BaseModel):
    prompt: str
    system: str | None = None


class LLMCompleteResponse(BaseModel):
    success: bool = True
    provider: str
    model: str
    content: str


class EmailSendRequest(BaseModel):
    to: str
    subject: str
    html: str
    text: str | None = None


class EmailSendResponse(BaseModel):
    success: bool = True
    provider: str
    id: str | None = None


class ApifyRunRequest(BaseModel):
    actor_id: str
    input: dict[str, Any] = Field(default_factory=dict)


class ApifyRunResponse(BaseModel):
    success: bool = True
    run_id: str
    status: str | None = None
    dataset_url: str | None = None


class GoogleSheetsAppendRequest(BaseModel):
    spreadsheet_id: str
    range_name: str = "Sheet1!A1"
    values: list[Any]


class GoogleSheetsAppendResponse(BaseModel):
    success: bool = True
    updated_range: str | None = None
    updated_rows: int | None = None


class SupabaseQueryRequest(BaseModel):
    table: str
    operation: Literal["select", "insert"] = "select"
    select: str = "*"
    limit: int = 10
    row: dict[str, Any] | None = None


class SupabaseQueryResponse(BaseModel):
    success: bool = True
    data: list[dict[str, Any]]


class HubSpotContactRequest(BaseModel):
    email: str
    firstname: str | None = None
    lastname: str | None = None
    properties: dict[str, Any] | None = None


class HubSpotContactResponse(BaseModel):
    success: bool = True
    id: str | None = None
    email: str


class StripeCustomerRequest(BaseModel):
    email: str
    name: str | None = None
    metadata: dict[str, str] | None = None


class StripeCustomerResponse(BaseModel):
    success: bool = True
    id: str
    email: str | None = None
