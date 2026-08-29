"""Safe error responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.integrations.base import IntegrationError
from app.observability import current_request_id

logger = logging.getLogger(__name__)


def _payload(code: str, message: str) -> dict:
    return {
        "error": {"code": code, "message": message},
        "request_id": current_request_id() or None,
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(f"http_{exc.status_code}", detail),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = sorted({".".join(str(p) for p in err["loc"][1:]) for err in exc.errors()})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_payload("invalid_request", f"Invalid fields: {', '.join(fields)}"),
        )

    @app.exception_handler(IntegrationError)
    async def _integration_error(_: Request, exc: IntegrationError) -> JSONResponse:
        logger.error(
            "upstream failure service=%s status=%s", exc.service, exc.status_code
        )
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=_payload("not_configured", f"{exc.service}: {exc.message}"),
            )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=_payload("upstream_error", f"Upstream service {exc.service} failed"),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error type=%s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload("internal_error", "Request failed"),
        )
