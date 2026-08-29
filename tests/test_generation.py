"""Citation validation and the insufficient-evidence rule."""

from __future__ import annotations

import pytest

from app.dependencies.services import get_llm_client
from tests.conftest import CLIENT_A, KEY_A, upload

TRANSCRIPT = "I call every new franchisee personally on their first day in business."


class FakeLLM:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.last_prompt: str | None = None

    async def complete_json(self, system: str, prompt: str) -> dict:
        self.last_prompt = prompt
        return self.payload


@pytest.fixture
def use_llm(client):
    def _install(payload: dict) -> FakeLLM:
        fake = FakeLLM(payload)
        client.app.dependency_overrides[get_llm_client] = lambda: fake
        return fake

    yield _install
    client.app.dependency_overrides.clear()


def _evidence_id(client) -> str:
    upload(client, CLIENT_A, KEY_A, TRANSCRIPT)
    hits = client.post(
        f"/v1/clients/{CLIENT_A}/search",
        headers={"X-API-Key": KEY_A},
        json={"query": "franchisee first day call"},
    ).json()["evidence"]
    return hits[0]["evidence_id"]


def test_anecdote_cites_real_evidence(client, use_llm):
    evidence_id = _evidence_id(client)
    fake = use_llm(
        {
            "anecdotes": [
                {
                    "setup": "Every franchisee opens alone.",
                    "event": "She calls each one on day one.",
                    "outcome": "They remember it years later.",
                    "relevance": "Shows the culture claim is real.",
                    "evidence_ids": [evidence_id],
                    "confidence": 0.9,
                }
            ]
        }
    )

    body = client.post(
        f"/v1/clients/{CLIENT_A}/anecdotes:search",
        headers={"X-API-Key": KEY_A},
        json={"theme": "franchisee first day call"},
    ).json()

    assert body["insufficient_evidence"] is False
    assert body["anecdotes"][0]["evidence_ids"] == [evidence_id]
    assert evidence_id in (fake.last_prompt or "")


def test_anecdote_with_fabricated_citation_is_discarded(client, use_llm):
    _evidence_id(client)
    use_llm(
        {
            "anecdotes": [
                {
                    "setup": "s",
                    "event": "e",
                    "outcome": "o",
                    "relevance": "r",
                    "evidence_ids": ["ev_does_not_exist"],
                    "confidence": 0.99,
                }
            ]
        }
    )

    body = client.post(
        f"/v1/clients/{CLIENT_A}/anecdotes:search",
        headers={"X-API-Key": KEY_A},
        json={"theme": "franchisee first day call"},
    ).json()

    assert body["anecdotes"] == []
    assert body["insufficient_evidence"] is True
    assert body["reason"]


def test_no_evidence_returns_insufficient_evidence(client, use_llm):
    use_llm({"anecdotes": []})
    body = client.post(
        f"/v1/clients/{CLIENT_A}/anecdotes:search",
        headers={"X-API-Key": KEY_A},
        json={"theme": "a theme with no ingested sources"},
    ).json()

    assert body["insufficient_evidence"] is True


def test_draft_review_demotes_claims_with_invalid_citations(client, use_llm):
    evidence_id = _evidence_id(client)
    use_llm(
        {
            "supported_claims": [
                {"claim": "She calls new franchisees.", "evidence_ids": [evidence_id]},
                {"claim": "She was 18 at the time.", "evidence_ids": ["ev_fake"]},
            ],
            "unsupported_claims": [
                {"claim": "She opened 35 locations.", "reason": "Not in the evidence."}
            ],
            "suggested_evidence": [
                {"evidence_id": evidence_id, "reason": "Direct support."},
                {"evidence_id": "ev_fake", "reason": "Should be dropped."},
            ],
        }
    )

    body = client.post(
        f"/v1/clients/{CLIENT_A}/drafts:review",
        headers={"X-API-Key": KEY_A},
        json={"draft_text": "When I started at 18 I called every franchisee."},
    ).json()

    assert body["supported_claims"] == [
        {"claim": "She calls new franchisees.", "evidence_ids": [evidence_id]}
    ]
    unsupported = {item["claim"] for item in body["unsupported_claims"]}
    assert "She was 18 at the time." in unsupported
    assert "She opened 35 locations." in unsupported
    assert [item["evidence_id"] for item in body["suggested_evidence"]] == [evidence_id]
    assert body["citations"] == [evidence_id]
