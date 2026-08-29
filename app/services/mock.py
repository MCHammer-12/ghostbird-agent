"""Back-compat alias for the mock knowledge engine.

The single definition now lives in ``app/services/retrieval.py``.
"""

from __future__ import annotations

from app.services.retrieval import MockRetrievalService, fixture_client_ids

__all__ = ["MockRetrievalService", "fixture_client_ids"]
