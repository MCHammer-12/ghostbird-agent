"""CRUD API contract tests using the in-memory repository."""

from __future__ import annotations

from tests.conftest import HEADERS


def test_health_endpoints(client):
    assert client.get("/healthz").json()["status"] == "ok"
    body = client.get("/readyz").json()
    assert body["status"] == "ready"
    assert body["database"] == "memory"
    assert body["database_ready"] is True


def test_client_crud(client):
    create = client.post(
        "/v1/clients",
        headers=HEADERS,
        json={"name": "Marisol Vance", "summary": "Industrial distribution"},
    )
    assert create.status_code == 201
    client_id = create.json()["id"]
    assert create.json()["name"] == "Marisol Vance"

    listed = client.get("/v1/clients?q=marisol", headers=HEADERS)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.patch(
        f"/v1/clients/{client_id}",
        headers=HEADERS,
        json={"writing_style": "Plainspoken"},
    )
    assert updated.status_code == 200
    assert updated.json()["writing_style"] == "Plainspoken"

    fetched = client.get(f"/v1/clients/{client_id}", headers=HEADERS)
    assert fetched.status_code == 200

    deleted = client.delete(f"/v1/clients/{client_id}", headers=HEADERS)
    assert deleted.status_code == 204
    assert client.get(f"/v1/clients/{client_id}", headers=HEADERS).status_code == 404


def test_upload_and_tag_flow(client):
    client_id = client.post(
        "/v1/clients",
        headers=HEADERS,
        json={"name": "Priya Chandrasekhar"},
    ).json()["id"]

    tag_id = client.post(
        f"/v1/clients/{client_id}/tags",
        headers=HEADERS,
        json={"name": "transcripts"},
    ).json()["id"]

    upload_id = client.post(
        f"/v1/clients/{client_id}/uploads",
        headers=HEADERS,
        json={
            "text": "We opened four new franchise territories last month.",
            "summary": "Growth update",
            "metadata": {"source_type": "interview"},
        },
    ).json()["id"]

    attach = client.post(
        f"/v1/clients/{client_id}/uploads/{upload_id}/tags/{tag_id}",
        headers=HEADERS,
    )
    assert attach.status_code == 204

    tags = client.get(
        f"/v1/clients/{client_id}/uploads/{upload_id}/tags",
        headers=HEADERS,
    ).json()
    assert len(tags) == 1
    assert tags[0]["name"] == "transcripts"

    filtered = client.get(
        f"/v1/clients/{client_id}/uploads?tag_id={tag_id}",
        headers=HEADERS,
    ).json()
    assert len(filtered) == 1
    assert filtered[0]["id"] == upload_id

    replaced = client.put(
        f"/v1/clients/{client_id}/uploads/{upload_id}/tags",
        headers=HEADERS,
        json={"tag_ids": []},
    )
    assert replaced.status_code == 200
    assert replaced.json() == []

    detach_missing = client.delete(
        f"/v1/clients/{client_id}/uploads/{upload_id}/tags/{tag_id}",
        headers=HEADERS,
    )
    assert detach_missing.status_code == 404


def test_duplicate_tag_name_is_rejected(client):
    client_id = client.post(
        "/v1/clients",
        headers=HEADERS,
        json={"name": "Desmond Okafor"},
    ).json()["id"]

    first = client.post(
        f"/v1/clients/{client_id}/tags",
        headers=HEADERS,
        json={"name": "meeting notes"},
    )
    assert first.status_code == 201

    second = client.post(
        f"/v1/clients/{client_id}/tags",
        headers=HEADERS,
        json={"name": "meeting notes"},
    )
    assert second.status_code == 409


def test_requires_api_key(client):
    response = client.get("/v1/clients")
    assert response.status_code == 401
