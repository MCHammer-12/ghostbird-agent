"""Back-compat alias for the shared cross-track contracts.

The single definition now lives in ``app/schemas/evidence.py``. This module
re-exports it so existing imports keep working and there is never a second
EvidenceCard class in the process.
"""

from __future__ import annotations

from app.schemas.evidence import (
    DraftReviewResponse,
    EvidenceCard,
    ExpandedEvidence,
    IngestionJob,
    IngestionStatus,
    SourceInput,
    SourceMetadata,
    SuggestedEvidence,
    SupportedClaim,
    UnsupportedClaim,
)

__all__ = [
    "DraftReviewResponse",
    "EvidenceCard",
    "ExpandedEvidence",
    "IngestionJob",
    "IngestionStatus",
    "SourceInput",
    "SourceMetadata",
    "SuggestedEvidence",
    "SupportedClaim",
    "UnsupportedClaim",
]
