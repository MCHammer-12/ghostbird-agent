from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.ghostbird.models import VoiceProfile


class SourceImportRequest(BaseModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    text: str = Field(min_length=1)
    purpose: str | None = None
    captured_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    speaker_map: dict[str, str] = Field(default_factory=dict)


class VoiceProfileResponse(BaseModel):
    profile: VoiceProfile | None
