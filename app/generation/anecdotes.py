"""Anecdote generation from bounded client evidence.

    authorize -> search_context -> bounded evidence to the model
    -> validate every evidence ID -> structured response
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from app.config import Settings
from app.generation.citations import evidence_is_sufficient, validate_citations
from app.generation.prompts import ANECDOTE_SYSTEM, anecdote_prompt
from app.integrations.llm import LLMClient
from app.isolation import allowed_evidence_ids
from app.schemas.api import Anecdote, AnecdoteSearchResponse
from app.schemas.shared import EvidenceCard

logger = logging.getLogger(__name__)

INSUFFICIENT_EVIDENCE = (
    "No client evidence strong enough to support an anecdote on this theme."
)


def _insufficient(reason: str = INSUFFICIENT_EVIDENCE) -> AnecdoteSearchResponse:
    return AnecdoteSearchResponse(anecdotes=[], insufficient_evidence=True, reason=reason)


async def find_anecdotes(
    llm: LLMClient,
    settings: Settings,
    theme: str,
    cards: Sequence[EvidenceCard],
) -> AnecdoteSearchResponse:
    if not evidence_is_sufficient(cards, settings):
        return _insufficient()

    data = await llm.complete_json(ANECDOTE_SYSTEM, anecdote_prompt(theme, cards))
    allowed = allowed_evidence_ids(cards)

    anecdotes: list[Anecdote] = []
    for item in data.get("anecdotes") or []:
        if not isinstance(item, dict):
            continue
        evidence_ids = validate_citations(item.get("evidence_ids") or [], allowed)
        if not evidence_ids:
            # Rule 5: an anecdote with no verifiable evidence is not returned.
            logger.warning("discarded anecdote with no valid citations")
            continue
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        anecdotes.append(
            Anecdote(
                setup=str(item.get("setup", "")),
                event=str(item.get("event", "")),
                outcome=str(item.get("outcome", "")),
                relevance=str(item.get("relevance", "")),
                evidence_ids=evidence_ids,
                confidence=max(0.0, min(confidence, 1.0)),
            )
        )

    if not anecdotes:
        return _insufficient()
    return AnecdoteSearchResponse(anecdotes=anecdotes)
