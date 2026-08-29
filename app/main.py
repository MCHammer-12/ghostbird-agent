from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.errors import register_error_handlers
from app.observability import RequestContextMiddleware, configure_logging
from app.routers import clients, ghostbird, health, tags, uploads

settings = get_settings()
static_directory = Path(__file__).parent / "static"

configure_logging(settings.environment)

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=(
        "Ghostbird CRUD API for clients, uploads, and tags, plus the ghostbird "
        "agent endpoints for voice profile and post generation."
    ),
)

app.add_middleware(RequestContextMiddleware)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

register_error_handlers(app)

app.include_router(health.router)
app.include_router(clients.router)
app.include_router(uploads.router)
app.include_router(tags.router)

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
