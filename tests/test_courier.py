"""Courier response normalization and schema generation.

Covers the two things the Courier provider must never get wrong: leaking model
reasoning into a user-facing answer, and handing Outlines a schema whose
properties are all optional.
"""

from __future__ import annotations

import asyncio

import pytest

from app.config import LLMProvider, Settings
from app.integrations.llm import (
    LLMClient,
    _courier_content,
    _drop_reasoning,
    _strip_courier_markers,
    json_schema_for,
)
from app.schemas.evidence import AnecdoteSearchResponse, DraftReviewResponse


def courier_settings(**overrides) -> Settings:
    fields = {
        "llm_provider": LLMProvider.COURIER,
        "courier_base_url": "https://courier.example/",
        "courier_api_key": "test-key",
        "courier_model": "Inkling",
    }
    return Settings(**{**fields, **overrides})


@pytest.mark.parametrize(
    "raw",
    [
        "<|content_thinking|>The user wants a greeting.<|content_text|>Courier connected<|end_message|>",
        "<|content_text|>Courier connected<|end_message|>",
        "<|content_thinking|>reasoning<|content_text|>  Courier connected  ",
        "Courier connected",
    ],
)
def test_only_content_text_survives(raw: str) -> None:
    assert _strip_courier_markers(raw) == "Courier connected"


def test_live_inkling_shape_is_reduced_to_its_answer() -> None:
    """Captured verbatim from a live Inkling reply (note the marker order:
    the reasoning span is terminated before content_text opens)."""
    raw = (
        '<|content_thinking|>The user wants me to reply with exactly: "Courier '
        "connected\"\n\nSo the response should be precisely:\nCourier connected"
        "<|end_message|><|message_model|><|content_text|>Courier connected<|end_message|>"
    )
    assert _strip_courier_markers(raw) == "Courier connected"


def test_reasoning_only_response_yields_no_text() -> None:
    assert _strip_courier_markers("<|content_thinking|>internal notes<|end_message|>") == ""


def test_content_text_marker_wins_over_earlier_ones() -> None:
    raw = "<|content_thinking|>a<|content_text|>b<|content_text|>final<|end_message|>"
    assert _strip_courier_markers(raw) == "final"


def test_courier_content_reads_the_openai_shape() -> None:
    data = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "<|content_thinking|>hmm<|content_text|>Courier connected<|end_message|>",
                    # A reasoning field on the message is never read.
                    "reasoning_content": "secret chain of thought",
                }
            }
        ]
    }
    assert _courier_content(data) == "Courier connected"


def test_courier_content_reads_the_bare_structured_shape() -> None:
    assert _courier_content({"content": '{"anecdotes": []}'}) == '{"anecdotes": []}'


def test_courier_content_survives_a_missing_body() -> None:
    assert _courier_content({"choices": []}) == ""
    assert _courier_content("not a dict") == ""


def test_reasoning_fields_are_dropped() -> None:
    assert _drop_reasoning({"Thought": "...", "reasoning": "...", "anecdotes": []}) == {
        "anecdotes": []
    }


@pytest.mark.parametrize("model", [AnecdoteSearchResponse, DraftReviewResponse])
def test_schema_marks_every_top_level_property_required(model) -> None:
    schema = json_schema_for(model)
    assert set(schema["required"]) == set(schema["properties"])


def test_courier_endpoint_joins_without_a_double_slash() -> None:
    assert (
        courier_settings().courier_endpoint("/v1/chat/completions")
        == "https://courier.example/v1/chat/completions"
    )


def test_courier_requires_url_key_and_model() -> None:
    assert courier_settings().llm_configured() is True
    assert courier_settings(courier_model="").llm_configured() is False
    assert courier_settings(courier_api_key="").llm_configured() is False
    assert courier_settings(courier_base_url="").llm_configured() is False


def test_structured_call_validates_and_strips_reasoning(monkeypatch) -> None:
    """The schema goes out; the thought field Outlines injects does not come back."""
    sent: dict = {}

    async def fake_request_json(method, url, *, service, headers, json, timeout):
        sent["url"] = url
        sent["auth"] = headers["Authorization"]
        sent["payload"] = json
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '<|content_text|>{"thought": "internal", "anecdotes": '
                            '[{"setup": "s", "event": "e", "outcome": "o", '
                            '"relevance": "r", "evidence_ids": ["ev_1"], '
                            '"confidence": 0.8}], "insufficient_evidence": false, '
                            '"reason": null}<|end_message|>'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.integrations.llm.request_json", fake_request_json)

    client = LLMClient(courier_settings())
    result = asyncio.run(client.complete_json("system", "prompt", AnecdoteSearchResponse))

    assert sent["url"] == "https://courier.example/v1/chat/completions"
    assert sent["auth"] == "Bearer test-key"
    assert sent["payload"]["model"] == "Inkling"
    assert sent["payload"]["response_format"]["type"] == "json_schema"
    assert "thought" not in result
    assert result["anecdotes"][0]["evidence_ids"] == ["ev_1"]


def test_structured_failure_falls_back_to_text_parsing(monkeypatch) -> None:
    """A schema Outlines cannot compile must not cost the whole request."""
    from app.integrations.base import IntegrationError

    calls: list[bool] = []

    async def fake_request_json(method, url, *, service, headers, json, timeout):
        constrained = "response_format" in json
        calls.append(constrained)
        if constrained:
            raise IntegrationError("courier", "schema compile failed", 400)
        return {"choices": [{"message": {"content": '```json\n{"anecdotes": []}\n```'}}]}

    monkeypatch.setattr("app.integrations.llm.request_json", fake_request_json)

    client = LLMClient(courier_settings())
    result = asyncio.run(client.complete_json("system", "prompt", AnecdoteSearchResponse))

    assert calls == [True, False]
    assert result["anecdotes"] == []
