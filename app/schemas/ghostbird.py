from typing import Any

from pydantic import BaseModel, Field

from app.ghostbird.models import StoredEvidence, VoiceProfile


class SourceUploadRequest(BaseModel):
    source_id: str
    title: str
    source_type: str
    text: str = Field(min_length=1)
    purpose: str | None = None
    captured_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    speaker_map: dict[str, str] = Field(default_factory=dict)


class EvidenceSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=50)


class EvidenceSearchResponse(BaseModel):
    evidence: list[StoredEvidence]


class VoiceProfileResponse(BaseModel):
    profile: VoiceProfile | None
