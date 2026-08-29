"""The REST contract Track 3 builds against."""

from __future__ import annotations

from tests.conftest import CLIENT_A, KEY_A, upload

TRANSCRIPT = """\
We awarded four new franchise territories last month, putting us at 35 locations.

I call every new franchisee personally on their first day. Renee in Tulsa still
brings it up.
"""


def test_health_endpoints(client):
    assert client.get("/healthz").json()["status"] == "ok"
    body = client.get("/readyz").json()
    assert body["status"] == "ready"
    assert body["retrieval_backend"] == "mock"


def test_upload_returns_a_job_and_status_reports_ready(client):
    response = upload(client, CLIENT_A, KEY_A, TRANSCRIPT)
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert response.json()["client_id"] == CLIENT_A

    status = client.get(
        f"/v1/clients/{CLIENT_A}/ingestion-jobs/{job_id}", headers={"X-API-Key": KEY_A}
    ).json()
    assert status["job_id"] == job_id
    assert status["status"] == "ready"
    assert status["stage"] == "complete"


def test_duplicate_upload_is_idempotent(client):
    first = upload(client, CLIENT_A, KEY_A, TRANSCRIPT, idem="same").json()["job_id"]
    second = upload(client, CLIENT_A, KEY_A, TRANSCRIPT, idem="same").json()["job_id"]
    assert first == second

    hits = client.post(
        f"/v1/clients/{CLIENT_A}/search",
        headers={"X-API-Key": KEY_A},
        json={"query": "franchise territories"},
    ).json()["evidence"]
    assert len({card["evidence_id"] for card in hits}) == len(hits)


def test_evidence_cards_carry_the_shared_contract_fields(client):
    upload(client, CLIENT_A, KEY_A, TRANSCRIPT)
    card = client.post(
        f"/v1/clients/{CLIENT_A}/search",
        headers={"X-API-Key": KEY_A},
        json={"query": "franchisee first day call", "top_k": 3},
    ).json()["evidence"][0]

    assert set(card) == {
        "evidence_id",
        "client_id",
        "excerpt",
        "source_id",
        "source_location",
        "type",
        "relevance_score",
    }

    opened = client.get(
        f"/v1/clients/{CLIENT_A}/evidence/{card['evidence_id']}",
        headers={"X-API-Key": KEY_A},
    ).json()
    assert opened["evidence_id"] == card["evidence_id"]
    assert opened["context"]


def test_incomplete_jobs_are_not_searchable(client, monkeypatch):
    from app.config import get_settings

    get_settings().mock_ingestion_delay_polls = 1
    upload(client, CLIENT_A, KEY_A, TRANSCRIPT, idem="pending")

    hits = client.post(
        f"/v1/clients/{CLIENT_A}/search",
        headers={"X-API-Key": KEY_A},
        json={"query": "franchise territories"},
    ).json()["evidence"]
    assert hits == []


def test_top_k_is_clamped(client):
    upload(client, CLIENT_A, KEY_A, TRANSCRIPT)
    response = client.post(
        f"/v1/clients/{CLIENT_A}/search",
        headers={"X-API-Key": KEY_A},
        json={"query": "franchise", "top_k": 10_000},
    )
    assert response.status_code == 200
    assert len(response.json()["evidence"]) <= get_max_top_k()


def get_max_top_k() -> int:
    from app.config import get_settings

    return get_settings().max_top_k


def test_empty_draft_is_rejected(client):
    response = client.post(
        f"/v1/clients/{CLIENT_A}/drafts:review",
        headers={"X-API-Key": KEY_A},
        json={"draft_text": "   "},
    )
    assert response.status_code == 400
