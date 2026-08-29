"""Draft review against client evidence.

Separates what the client's own material supports from what it does not, and
points every supported claim back to a real evidence ID.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from app.config import Settings
from app.generation.citations import validate_citations
from app.generation.prompts import DRAFT_REVIEW_SYSTEM, draft_review_prompt
from app.integrations.llm import LLMClient
from app.isolation import allowed_evidence_ids
from app.schemas.shared import (
    DraftReviewResponse,
    EvidenceCard,
    SuggestedEvidence,
    SupportedClaim,
    UnsupportedClaim,
)

logger = logging.getLogger(__name__)

NO_EVIDENCE_REASON = "No supporting client evidence was found."


async def review_draft(
    llm: LLMClient,
    settings: Settings,
    draft_text: str,
    cards: Sequence[EvidenceCard],
) -> DraftReviewResponse:
    if not cards:
        return DraftReviewResponse()

    data = await llm.complete_json(
        DRAFT_REVIEW_SYSTEM,
        draft_review_prompt(draft_text, cards),
        DraftReviewResponse,
    )
    allowed = allowed_evidence_ids(cards)

    supported: list[SupportedClaim] = []
    unsupported: list[UnsupportedClaim] = []

    for item in data.get("supported_claims") or []:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim", "")).strip()
        if not claim:
            continue
        evidence_ids = validate_citations(item.get("evidence_ids") or [], allowed)
        if evidence_ids:
            supported.append(SupportedClaim(claim=claim, evidence_ids=evidence_ids))
        else:
            # A "supported" claim whose citations do not exist is unsupported.
            logger.warning("demoted supported claim with no valid citations")
            unsupported.append(UnsupportedClaim(claim=claim, reason=NO_EVIDENCE_REASON))

    for item in data.get("unsupported_claims") or []:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim", "")).strip()
        if not claim:
            continue
        unsupported.append(
            UnsupportedClaim(
                claim=claim,
                reason=str(item.get("reason") or NO_EVIDENCE_REASON),
            )
        )

    suggested: list[SuggestedEvidence] = []
    for item in data.get("suggested_evidence") or []:
        if not isinstance(item, dict):
            continue
        evidence_ids = validate_citations([item.get("evidence_id")], allowed)
        if evidence_ids:
            suggested.append(
                SuggestedEvidence(
                    evidence_id=evidence_ids[0],
                    reason=str(item.get("reason", "")),
                )
            )

    citations: list[str] = []
    for evidence_id in [eid for claim in supported for eid in claim.evidence_ids] + [
        item.evidence_id for item in suggested
    ]:
        if evidence_id not in citations:
            citations.append(evidence_id)

    return DraftReviewResponse(
        supported_claims=supported,
        unsupported_claims=unsupported,
        suggested_evidence=suggested,
        citations=citations,
    )
