"""Client isolation: authorization happens before retrieval, in code."""

from __future__ import annotations

from tests.conftest import CLIENT_A, CLIENT_B, KEY_A, KEY_B, upload

SECRET = "We shipped the Tulsa welcome call habit and it changed franchisee retention."


def test_missing_key_is_rejected(client):
    response = client.post(f"/v1/clients/{CLIENT_A}/search", json={"query": "welcome"})
    assert response.status_code == 401


def test_invalid_key_is_rejected(client):
    response = client.post(
        f"/v1/clients/{CLIENT_A}/search",
        headers={"X-API-Key": "nope"},
        json={"query": "welcome"},
    )
    assert response.status_code == 401


def test_key_cannot_reach_another_clients_scope(client):
    response = client.post(
        f"/v1/clients/{CLIENT_A}/search",
        headers={"X-API-Key": KEY_B},
        json={"query": "welcome"},
    )
    assert response.status_code == 403


def test_client_a_content_is_invisible_to_client_b(client):
    assert upload(client, CLIENT_A, KEY_A, SECRET).status_code == 202

    a_hits = client.post(
        f"/v1/clients/{CLIENT_A}/search",
        headers={"X-API-Key": KEY_A},
        json={"query": "welcome call retention"},
    ).json()["evidence"]
    assert a_hits, "client A should find its own evidence"
    assert all(card["client_id"] == CLIENT_A for card in a_hits)

    b_hits = client.post(
        f"/v1/clients/{CLIENT_B}/search",
        headers={"X-API-Key": KEY_B},
        json={"query": "welcome call retention"},
    ).json()["evidence"]
    assert b_hits == []

    evidence_id = a_hits[0]["evidence_id"]
    leaked = client.get(
        f"/v1/clients/{CLIENT_B}/evidence/{evidence_id}", headers={"X-API-Key": KEY_B}
    )
    assert leaked.status_code == 404


def test_error_body_carries_a_request_id_and_no_source_text(client):
    upload(client, CLIENT_A, KEY_A, SECRET)
    response = client.get(
        f"/v1/clients/{CLIENT_A}/evidence/ev_missing", headers={"X-API-Key": KEY_A}
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "http_404"
    assert body["request_id"]
    assert "Tulsa" not in response.text
