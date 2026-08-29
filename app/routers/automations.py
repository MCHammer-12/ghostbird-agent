from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.dependencies.auth import verify_api_key
from app.integrations.apify_ import ApifyClient
from app.integrations.base import IntegrationError
from app.integrations.crm import CRMClient
from app.integrations.email import EmailClient
from app.integrations.google_ import GoogleClient
from app.integrations.llm import LLMClient
from app.integrations.stripe_ import StripeClient
from app.integrations.supabase_ import SupabaseClient
from app.schemas.automations import (
    ApifyRunRequest,
    ApifyRunResponse,
    EmailSendRequest,
    EmailSendResponse,
    GoogleSheetsAppendRequest,
    GoogleSheetsAppendResponse,
    HubSpotContactRequest,
    HubSpotContactResponse,
    LLMCompleteRequest,
    LLMCompleteResponse,
    StripeCustomerRequest,
    StripeCustomerResponse,
    SupabaseQueryRequest,
    SupabaseQueryResponse,
)

router = APIRouter(prefix="/automations", tags=["automations"])


def _require(action: str) -> None:
    settings = get_settings()
    missing = settings.required_for_action(action)
    if missing:
        raise HTTPException(status_code=503, detail={"missing": missing})


def _handle_integration_error(exc: IntegrationError) -> HTTPException:
    return HTTPException(status_code=502, detail={"service": exc.service, "message": exc.message})


@router.post("/llm/complete", response_model=LLMCompleteResponse)
async def llm_complete(
    body: LLMCompleteRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    _require("llm_complete")
    try:
        result = await LLMClient(get_settings()).complete(body.prompt, body.system)
    except IntegrationError as exc:
        raise _handle_integration_error(exc) from exc
    return {"success": True, **result}


@router.post("/email/send", response_model=EmailSendResponse)
async def email_send(
    body: EmailSendRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    _require("email_send")
    try:
        result = await EmailClient(get_settings()).send(body.to, body.subject, body.html, body.text)
    except IntegrationError as exc:
        raise _handle_integration_error(exc) from exc
    return {"success": True, **result}


@router.post("/apify/run", response_model=ApifyRunResponse)
async def apify_run(
    body: ApifyRunRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    _require("apify_run")
    try:
        result = await ApifyClient(get_settings()).run_actor(body.actor_id, body.input)
    except IntegrationError as exc:
        raise _handle_integration_error(exc) from exc
    return {"success": True, **result}


@router.post("/google/sheets/append", response_model=GoogleSheetsAppendResponse)
async def google_sheets_append(
    body: GoogleSheetsAppendRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    _require("google_sheets_append")
    try:
        result = await GoogleClient(get_settings()).append_sheet_row(
            body.spreadsheet_id,
            body.range_name,
            body.values,
        )
    except IntegrationError as exc:
        raise _handle_integration_error(exc) from exc
    return {"success": True, **result}


@router.post("/supabase/query", response_model=SupabaseQueryResponse)
async def supabase_query(
    body: SupabaseQueryRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    _require("supabase_query")
    client = SupabaseClient(get_settings())
    try:
        if body.operation == "insert":
            if not body.row:
                raise HTTPException(status_code=400, detail="row is required for insert")
            data = await client.insert(body.table, body.row)
        else:
            data = await client.query(body.table, body.select, body.limit)
    except IntegrationError as exc:
        raise _handle_integration_error(exc) from exc
    return {"success": True, "data": data}


@router.post("/crm/hubspot/contact", response_model=HubSpotContactResponse)
async def hubspot_contact(
    body: HubSpotContactRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    _require("hubspot_contact")
    try:
        result = await CRMClient(get_settings()).upsert_hubspot_contact(
            body.email,
            body.firstname,
            body.lastname,
            body.properties,
        )
    except IntegrationError as exc:
        raise _handle_integration_error(exc) from exc
    return {"success": True, **result}


@router.post("/stripe/customer", response_model=StripeCustomerResponse)
async def stripe_customer(
    body: StripeCustomerRequest,
    _: None = Depends(verify_api_key),
) -> dict[str, Any]:
    _require("stripe_customer")
    try:
        result = await StripeClient(get_settings()).create_customer(body.email, body.name, body.metadata)
    except IntegrationError as exc:
        raise _handle_integration_error(exc) from exc
    return {"success": True, **result}
