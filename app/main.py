from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import automations, health, webhooks

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Clone-and-deploy automation endpoints for FastAPI Cloud",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router)
app.include_router(automations.router)
app.include_router(webhooks.router)
