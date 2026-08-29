from pydantic import BaseModel

from app.ghostbird.models import VoiceProfile


class VoiceProfileResponse(BaseModel):
    profile: VoiceProfile | None
