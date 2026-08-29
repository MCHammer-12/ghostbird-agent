"""MockRetrievalService: the Track 1 contract Track 2 builds against.

These tests exercise app/services/retrieval.py directly, with no API layer, so
they stay green while Track 2's routers are still being wired.
"""

from __future__ import annotations

import asyncio

import pytest

from app.schemas.evidence import EvidenceCard, ExpandedEvidence, IngestionStatus
from app.services.retrieval import (
    MockRetrievalService,
    RetrievalService,
    fixture_client_ids,
)

CLIENT_A = "bloom_bar"
CLIENT_B = "vance_kinder"

CARD_FIELDS = {
    "evidence_id",
    "client_id",
    "excerpt",
    "source_id",
    "source_location",
    "type",
    "relevance_score",
}


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def service() -> MockRetrievalService:
    return MockRetrievalService(load_fixtures=True)


# --- fixture data ----------------------------------------------------------


def test_fixture_clients_are_loaded():
    assert set(fixture_client_ids()) == {"bloom_bar", "ridgeline", "vance_kinder"}


def test_search_returns_relevant_client_evidence(service):
    cards = run(
        service.search_context(CLIENT_A, "calling every new franchisee on day one", {})
    )
    assert cards, "expected fixture evidence for the day-one welcome call"
    assert all(isinstance(card, EvidenceCard) for card in cards)
    assert "franchisee" in cards[0].excerpt.lower()


def test_results_are_ordered_by_relevance(service):
    cards = run(service.search_context(CLIENT_A, "franchise territories", {"top_k": 5}))
    scores = [card.relevance_score for card in cards]
    assert scores == sorted(scores, reverse=True)


def test_every_card_matches_the_shared_contract(service):
    cards = run(service.search_context(CLIENT_B, "fastener distribution customers", {}))
    assert cards
    for card in cards:
        assert set(card.model_dump()) == CARD_FIELDS
        assert card.client_id == CLIENT_B
        assert card.evidence_id and card.source_id and card.source_location
        assert 0.0 <= card.relevance_score <= 1.0


def test_evidence_ids_are_stable_across_instances():
    first = run(MockRetrievalService(load_fixtures=True).search_context(CLIENT_A, "franchise growth", {}))
    second = run(MockRetrievalService(load_fixtures=True).search_context(CLIENT_A, "franchise growth", {}))
    assert [c.evidence_id for c in first] == [c.evidence_id for c in second]


def test_top_k_is_respected(service):
    cards = run(service.search_context(CLIENT_A, "franchise", {"top_k": 2}))
    assert len(cards) <= 2


def test_empty_query_returns_nothing(service):
    assert run(service.search_context(CLIENT_A, "   ", {})) == []


# --- get_evidence ----------------------------------------------------------


def test_get_evidence_expands_with_surrounding_context(service):
    card = run(service.search_context(CLIENT_A, "franchisee first day", {}))[0]
    expanded = run(service.get_evidence(CLIENT_A, card.evidence_id))

    assert isinstance(expanded, ExpandedEvidence)
    assert expanded.evidence_id == card.evidence_id
    assert expanded.source_id == card.source_id
    assert expanded.context
    assert card.excerpt in expanded.context


def test_unknown_evidence_id_returns_none(service):
    assert run(service.get_evidence(CLIENT_A, "ev_does_not_exist")) is None


# --- client isolation ------------------------------------------------------


def test_search_never_crosses_clients(service):
    a_cards = run(service.search_context(CLIENT_A, "franchise conference Renee Tulsa", {}))
    assert a_cards
    b_cards = run(service.search_context(CLIENT_B, "franchise conference Renee Tulsa", {}))

    assert all(card.client_id == CLIENT_A for card in a_cards)
    assert all(card.client_id == CLIENT_B for card in b_cards)
    assert not ({c.evidence_id for c in a_cards} & {c.evidence_id for c in b_cards})


def test_get_evidence_is_client_scoped(service):
    card = run(service.search_context(CLIENT_A, "franchisee first day", {}))[0]
    assert run(service.get_evidence(CLIENT_B, card.evidence_id)) is None


def test_uploaded_source_is_invisible_to_another_client(service):
    secret = "The Tulsa welcome call habit changed franchisee retention entirely."
    run(service.ingest_source(CLIENT_A, secret, {"idempotency_key": "k1"}))

    b_cards = run(service.search_context(CLIENT_B, "Tulsa welcome call retention", {}))
    assert all("Tulsa welcome call habit" not in card.excerpt for card in b_cards)


# --- ingestion -------------------------------------------------------------


def test_ingest_makes_new_text_searchable(service):
    run(
        service.ingest_source(
            CLIENT_B,
            "We shipped a new same-day fastener kitting service this quarter.",
            {"source_type": "interview", "external_id": "Interview 9", "idempotency_key": "u1"},
        )
    )
    cards = run(service.search_context(CLIENT_B, "same-day fastener kitting service", {}))
    assert any("kitting" in card.excerpt for card in cards)
    assert any(card.source_location.startswith("Interview 9") for card in cards)


def test_duplicate_upload_is_idempotent(service):
    text = "A duplicate transcript body about warehouse automation."
    meta = {"source_type": "interview", "idempotency_key": "same"}
    first = run(service.ingest_source(CLIENT_B, text, meta))
    second = run(service.ingest_source(CLIENT_B, text, meta))

    assert first == second
    cards = run(service.search_context(CLIENT_B, "duplicate transcript warehouse automation", {}))
    assert len({card.evidence_id for card in cards}) == len(cards)


def test_ingestion_status_reports_ready(service):
    job_id = run(service.ingest_source(CLIENT_A, "Some transcript text.", {}))
    job = run(service.get_ingestion_status(CLIENT_A, job_id))
    assert job is not None
    assert job.status is IngestionStatus.READY
    assert job.stage == "complete"


def test_unknown_job_returns_none(service):
    assert run(service.get_ingestion_status(CLIENT_A, "job_nope")) is None


def test_job_lookup_is_client_scoped(service):
    job_id = run(service.ingest_source(CLIENT_A, "Some transcript text.", {}))
    assert run(service.get_ingestion_status(CLIENT_B, job_id)) is None


class _DelaySettings:
    mock_ingestion_delay_polls = 1


def test_incomplete_ingestion_is_not_searchable():
    service = MockRetrievalService(_DelaySettings(), load_fixtures=True)
    run(
        service.ingest_source(
            CLIENT_A, "Pending text about a brand new territory award.", {}
        )
    )

    cards = run(service.search_context(CLIENT_A, "pending brand new territory award", {}))
    assert all("Pending text" not in card.excerpt for card in cards)


# --- contract shape --------------------------------------------------------


def test_mock_satisfies_the_retrieval_protocol(service):
    assert isinstance(service, RetrievalService)
