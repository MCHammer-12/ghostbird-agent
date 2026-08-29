"""Binding point for Track 1's real implementation.

Track 1 replaces the body of this class with calls into its own service layer
(Supabase/pgvector, chunking, embeddings, semantic search). Nothing above this
file changes when it does: routers, generation, and Track 3 all keep talking to
the RetrievalService protocol.

Track 2 must not import Track 1's models, tables, or SQL here (Rule 2).
"""

from __future__ import annotations

from typing import Any

from app.schemas.shared import EvidenceCard, ExpandedEvidence, IngestionJob

_NOT_WIRED = (
    "Track 1 is not wired up yet. Implement app/services/track1.py, or run "
    "with RETRIEVAL_BACKEND=mock."
)


class Track1RetrievalService:
    """Implements app.services.protocol.RetrievalService."""

    async def ingest_source(
        self,
        client_id: str,
        text: str,
        metadata: dict[str, Any],
    ) -> str:
        raise NotImplementedError(_NOT_WIRED)

    async def get_ingestion_status(
        self,
        client_id: str,
        job_id: str,
    ) -> IngestionJob | None:
        raise NotImplementedError(_NOT_WIRED)

    async def search_context(
        self,
        client_id: str,
        query: str,
        filters: dict[str, Any],
    ) -> list[EvidenceCard]:
        raise NotImplementedError(_NOT_WIRED)

    async def get_evidence(
        self,
        client_id: str,
        evidence_id: str,
    ) -> ExpandedEvidence | None:
        raise NotImplementedError(_NOT_WIRED)
