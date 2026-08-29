"""Request IDs and privacy-safe logging (Track 2 ownership).

Logs carry identifiers, routes, statuses, and timings. They never carry source
text, draft text, excerpts, or credentials.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

_request_id: ContextVar[str] = ContextVar("request_id", default="")

logger = logging.getLogger("ghostbird.access")


def current_request_id() -> str:
    return _request_id.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = _request_id.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            _request_id.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        route = request.scope.get("route")
        logger.info(
            "%s %s %s %sms",
            request.method,
            getattr(route, "path", request.url.path),
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )
        return response


def configure_logging(environment: str) -> None:
    level = logging.INFO if environment == "production" else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
