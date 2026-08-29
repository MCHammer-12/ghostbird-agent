"""Client-isolation enforcement (Rule 4).

Track 1 filters by client at the storage layer. Track 2 checks the result
anyway, on the way out, because isolation is enforced in more than one place
and never only in prompts.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence

from app.schemas.shared import EvidenceCard

logger = logging.getLogger(__name__)


class ClientScopeViolation(Exception):
    """Raised when retrieval returns content outside the requested client."""


def enforce_client_scope(client_id: str, cards: Sequence[EvidenceCard]) -> list[EvidenceCard]:
    """Fail closed if any card belongs to a different client."""
    foreign = {card.client_id for card in cards if card.client_id != client_id}
    if foreign:
        # IDs only. Never log excerpts.
        logger.critical(
            "client scope violation",
            extra={"requested_client": client_id, "foreign_client_count": len(foreign)},
        )
        raise ClientScopeViolation(
            f"Retrieval returned evidence outside client {client_id!r}"
        )
    return list(cards)


def allowed_evidence_ids(cards: Iterable[EvidenceCard]) -> set[str]:
    """The only evidence IDs a generated response may cite."""
    return {card.evidence_id for card in cards}
