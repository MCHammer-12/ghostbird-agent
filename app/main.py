from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.errors import register_error_handlers
from app.observability import RequestContextMiddleware, configure_logging
from app.routers import (
    anecdotes,
    automations,
    drafts,
    evidence,
    ghostbird,
    health,
    search,
    sources,
    webhooks,
)

settings = get_settings()
static_directory = Path(__file__).parent / "static"

configure_logging(settings.environment)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Ghostbird Track 2: the API Track 3 consumes. Client evidence is reached "
        "only through the Track 1 retrieval contract, never by querying a "
        "database directly."
    ),
)

# Request IDs and privacy-safe access logging, outermost so every response
# carries X-Request-ID.
app.add_middleware(RequestContextMiddleware)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Safe error envelopes: upstream messages never reach the caller verbatim.
register_error_handlers(app)

# Health / probes.
app.include_router(health.router)

# Ghostbird Track 2 API (/v1/clients/{client_id}/...).
app.include_router(sources.router)
app.include_router(search.router)
app.include_router(evidence.router)
app.include_router(anecdotes.router)
app.include_router(drafts.router)

# Template automation endpoints, unchanged.
app.include_router(automations.router)
app.include_router(webhooks.router)

app.mount("/static", StaticFiles(directory=static_directory), name="static")


@app.get("/", include_in_schema=False)
def product_ui() -> FileResponse:
    """Serve the standalone Ghostbird product prototype."""
    return FileResponse(static_directory / "index.html")


@app.get("/styles.css", include_in_schema=False)
def product_styles() -> FileResponse:
    return FileResponse(static_directory / "styles.css")


@app.get("/app.js", include_in_schema=False)
def product_script() -> FileResponse:
    return FileResponse(static_directory / "app.js")


@app.get("/ghostbird-logo.png", include_in_schema=False)
def product_logo() -> FileResponse:
    return FileResponse(static_directory / "ghostbird-logo.png")


app.include_router(ghostbird.router)
