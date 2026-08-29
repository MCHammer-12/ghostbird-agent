"""Citation validation (Track 2 ownership).

Every evidence ID a model produces is checked against the bounded set that was
actually retrieved for this client. Anything else is dropped: an unverifiable
citation is indistinguishable from a fabricated one.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence

from app.config import Settings
from app.schemas.shared import EvidenceCard

logger = logging.getLogger(__name__)


def validate_citations(candidate_ids: Iterable[object], allowed_ids: set[str]) -> list[str]:
    """Keep only real evidence IDs, de-duplicated, in order."""
    kept: list[str] = []
    dropped = 0
    for value in candidate_ids:
        evidence_id = value if isinstance(value, str) else str(value)
        if evidence_id in allowed_ids:
            if evidence_id not in kept:
                kept.append(evidence_id)
        else:
            dropped += 1
    if dropped:
        logger.warning("dropped %s citation(s) not in the retrieved set", dropped)
    return kept


def evidence_is_sufficient(cards: Sequence[EvidenceCard], settings: Settings) -> bool:
    """Whether retrieval was strong enough to attempt generation (Rule 5)."""
    strong = [card for card in cards if card.relevance_score >= settings.min_relevance_score]
    return len(strong) >= settings.min_evidence_count
