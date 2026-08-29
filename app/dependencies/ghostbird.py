from functools import lru_cache

from app.config import get_settings
from app.ghostbird.model_runner import ConfiguredStructuredModel
from app.ghostbird.repository import InMemoryEvidenceRepository, SupabaseEvidenceRepository
from app.ghostbird.service import GhostbirdService
from app.integrations.llm import LLMClient
from app.integrations.supabase_ import SupabaseClient


@lru_cache
def get_ghostbird_service() -> GhostbirdService:
    settings = get_settings()
    model = ConfiguredStructuredModel(LLMClient(settings))
    if settings.supabase_url and settings.supabase_service_role_key:
        repository = SupabaseEvidenceRepository(SupabaseClient(settings))
    else:
        repository = InMemoryEvidenceRepository()
    return GhostbirdService(model, repository)
