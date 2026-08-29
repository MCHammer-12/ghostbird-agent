"""Open one evidence record so Track 3 can show the exact source context."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import require_client_access
from app.dependencies.services import get_retrieval_service
from app.isolation import enforce_client_scope
from app.schemas.shared import ExpandedEvidence
from app.services.protocol import RetrievalService

router = APIRouter(prefix="/v1/clients/{client_id}", tags=["evidence"])


@router.get(
    "/evidence/{evidence_id}",
    response_model=ExpandedEvidence,
    summary="Open source evidence",
)
async def get_evidence(
    evidence_id: str,
    client_id: str = Depends(require_client_access),
    service: RetrievalService = Depends(get_retrieval_service),
) -> ExpandedEvidence:
    evidence = await service.get_evidence(client_id, evidence_id)
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found"
        )
    # Verify ownership before returning, even though Track 1 filtered already.
    enforce_client_scope(client_id, [evidence])
    return evidence
