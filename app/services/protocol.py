"""Back-compat alias for the Track 1 <-> Track 2 contract.

The single definition now lives in ``app/services/retrieval.py``.
"""

from __future__ import annotations

from app.services.retrieval import (
    FILTER_TOP_K,
    METADATA_IDEMPOTENCY_KEY,
    RetrievalService,
)

__all__ = ["FILTER_TOP_K", "METADATA_IDEMPOTENCY_KEY", "RetrievalService"]
