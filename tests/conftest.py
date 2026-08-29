from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

API_KEY = "test-key"
HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("API_KEY", API_KEY)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    from app.config import get_settings
    from app.dependencies.db import clear_repository_cache
    from app.dependencies.ghostbird import get_ghostbird_service

    get_settings.cache_clear()
    clear_repository_cache()
    get_ghostbird_service.cache_clear()

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
    clear_repository_cache()
    get_ghostbird_service.cache_clear()
