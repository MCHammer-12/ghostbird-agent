from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

CLIENT_A = "vance_kinder"
CLIENT_B = "bloom_bar"

KEY_A = "key-a"
KEY_B = "key-b"

API_KEYS = [
    {"key": KEY_A, "principal_id": "writer_a", "client_ids": [CLIENT_A]},
    {"key": KEY_B, "principal_id": "writer_b", "client_ids": [CLIENT_B]},
]


@pytest.fixture
def client(monkeypatch) -> TestClient:
    # Pinned so the suite does not inherit a developer's .env: the isolation
    # tests assume an empty mock, and the LLM provider must be one no test
    # actually calls out to.
    monkeypatch.setenv("API_KEYS", json.dumps(API_KEYS))
    monkeypatch.setenv("RETRIEVAL_BACKEND", "mock")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("MOCK_INGESTION_DELAY_POLLS", "0")
    monkeypatch.setenv("MOCK_LOAD_FIXTURES", "false")

    from app.config import get_settings
    from app.dependencies.services import _build_retrieval_service

    get_settings.cache_clear()
    _build_retrieval_service.cache_clear()

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
    _build_retrieval_service.cache_clear()


def upload(client: TestClient, client_id: str, key: str, text: str, idem: str = "k1"):
    return client.post(
        f"/v1/clients/{client_id}/sources",
        headers={"X-API-Key": key},
        json={
            "text": text,
            "metadata": {"source_type": "interview", "external_id": "Interview 1"},
            "idempotency_key": idem,
        },
    )
