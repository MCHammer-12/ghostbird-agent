"""The Track 2 API contract (docs/TRACKS.md, "Shared Contracts" + "Required REST API").

This module is the single definition of every object that crosses a track
boundary. Track 1 produces EvidenceCards, Track 2 consumes and returns them,
Track 3 renders them (Rule 3). If a shape here changes, all three tracks agree
first.

``app/schemas/shared.py`` and ``app/schemas/api.py`` re-export from here so the
older import paths keep working; there is only one definition of each model.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared contract 1 — SourceInput
# ---------------------------------------------------------------------------


class IngestionStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class SourceMetadata(BaseModel):
    """Metadata preserved alongside an uploaded source."""

    source_type: str = Field(examples=["interview"])
    captured_at: datetime | None = None
    external_id: str | None = None


class SourceInput(BaseModel):
    """Contract 1 — used when a transcript is uploaded."""

    client_id: str
    text: str
    metadata: SourceMetadata
    idempotency_key: str


class IngestionJob(BaseModel):
    """What Track 1's ``get_ingestion_status`` reports back."""

    job_id: str
    status: IngestionStatus
    stage: str


# ---------------------------------------------------------------------------
# Shared contract 2 — EvidenceCard
# ---------------------------------------------------------------------------


class EvidenceCard(BaseModel):
    """Contract 2 — the object passed Track 1 -> Track 2 -> Track 3.

    Every evidence result must belong to the requested client, carry a stable
    evidence ID, and carry enough source information to verify its origin.

    ``type`` is deliberately an open string: docs/TRACKS.md uses both
    "anecdote" and "story" for this field. Agree a closed vocabulary under
    Rule 3 before narrowing it.
    """

    evidence_id: str = Field(examples=["ev_123"])
    client_id: str = Field(examples=["client-a"])
    excerpt: str
    source_id: str = Field(examples=["src_123"])
    source_location: str = Field(examples=["Interview 1, segment 14"])
    type: str = Field(examples=["anecdote"])
    relevance_score: float


class ExpandedEvidence(EvidenceCard):
    """What ``GET /v1/clients/{client_id}/evidence/{evidence_id}`` returns.

    Adds the surrounding source passage so Track 3 can show the exact
    supporting transcript context.
    """

    context: str | None = None


# ---------------------------------------------------------------------------
# Shared contract 3 — DraftReviewResponse
# ---------------------------------------------------------------------------


class SupportedClaim(BaseModel):
    claim: str
    evidence_ids: list[str]


class UnsupportedClaim(BaseModel):
    claim: str
    reason: str


class SuggestedEvidence(BaseModel):
    evidence_id: str
    reason: str


class DraftReviewResponse(BaseModel):
    """Contract 3 — every client-specific conclusion points back to evidence."""

    supported_claims: list[SupportedClaim] = Field(default_factory=list)
    unsupported_claims: list[UnsupportedClaim] = Field(default_factory=list)
    suggested_evidence: list[SuggestedEvidence] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Track 2 REST request/response models
# ---------------------------------------------------------------------------


class SourceUploadRequest(BaseModel):
    """Body of ``POST /v1/clients/{client_id}/sources``.

    ``client_id`` is optional here because it is already in the path; when
    present it must match the path (Rule 4).
    """

    text: str
    metadata: SourceMetadata
    idempotency_key: str
    client_id: str | None = None


class SourceUploadResponse(BaseModel):
    job_id: str
    client_id: str
    status: IngestionStatus = IngestionStatus.QUEUED


class IngestionJobResponse(BaseModel):
    """Body of ``GET /v1/clients/{client_id}/ingestion-jobs/{job_id}``."""

    job_id: str
    status: IngestionStatus
    stage: str


class SearchRequest(BaseModel):
    """Body of ``POST /v1/clients/{client_id}/search``."""

    query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    top_k: int | None = None


class SearchResponse(BaseModel):
    """Evidence only. This endpoint does not generate a story."""

    evidence: list[EvidenceCard] = Field(default_factory=list)


class AnecdoteSearchRequest(BaseModel):
    """Body of ``POST /v1/clients/{client_id}/anecdotes:search``."""

    theme: str


class Anecdote(BaseModel):
    setup: str
    event: str
    outcome: str
    relevance: str
    evidence_ids: list[str]
    confidence: float


class AnecdoteSearchResponse(BaseModel):
    """Rule 5: weak evidence returns insufficient evidence, not a story.

    ``insufficient_evidence`` and ``reason`` are the Track 2 shape for the
    insufficient-evidence result docs/TRACKS.md requires but does not spell
    out. Confirm under Rule 3 before Track 3 depends on the field names.
    """

    anecdotes: list[Anecdote] = Field(default_factory=list)
    insufficient_evidence: bool = False
    reason: str | None = None


class DraftReviewRequest(BaseModel):
    """Body of ``POST /v1/clients/{client_id}/drafts:review``."""

    draft_text: str


# ---------------------------------------------------------------------------
# Safe error envelope
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Safe error envelope. Never carries source text or credentials."""

    error: ErrorDetail
    request_id: str | None = None
