"""Back-compat alias for the Track 2 REST request/response models.

The single definition now lives in ``app/schemas/evidence.py``.
"""

from __future__ import annotations

from app.schemas.evidence import (
    Anecdote,
    AnecdoteSearchRequest,
    AnecdoteSearchResponse,
    DraftReviewRequest,
    ErrorDetail,
    ErrorResponse,
    IngestionJobResponse,
    SearchRequest,
    SearchResponse,
    SourceUploadRequest,
    SourceUploadResponse,
)

__all__ = [
    "Anecdote",
    "AnecdoteSearchRequest",
    "AnecdoteSearchResponse",
    "DraftReviewRequest",
    "ErrorDetail",
    "ErrorResponse",
    "IngestionJobResponse",
    "SearchRequest",
    "SearchResponse",
    "SourceUploadRequest",
    "SourceUploadResponse",
]
