from enum import StrEnum
from functools import lru_cache

import json

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class RetrievalBackend(StrEnum):
    """Which implementation of the Track 1 contract to bind at startup.

    ``mock`` is the local-development default: MockRetrievalService, backed by
    the synthetic Ghostbird fixtures. ``track1`` binds Track 1's real service
    once it lands, with no change to the Track 2 API.
    """

    MOCK = "mock"
    TRACK1 = "track1"


class APIKeyRecord(BaseModel):
    """One Ghostbird API key and the clients it may reach.

    Client authorization is a property of the key, checked in code before any
    retrieval happens (docs/TRACKS.md, Track 2 Security Rule).
    """

    key: str
    principal_id: str
    client_ids: list[str] = Field(default_factory=list)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    app_name: str = "FastAPI Cloud Automation"
    environment: str = "development"
    api_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]
    webhook_secret: str = ""

    # Ghostbird / Track 2
    #
    # api_keys is the Ghostbird auth source: a JSON list of
    # {"key", "principal_id", "client_ids"}. When it is empty, the template's
    # single API_KEY is accepted for every client -- convenient locally, but it
    # grants no isolation, so set API_KEYS to demo or test client scoping.
    retrieval_backend: RetrievalBackend = RetrievalBackend.MOCK
    api_keys: list[APIKeyRecord] = Field(default_factory=list)

    # Retrieval bounds. top_k is clamped to max_top_k before Track 1 is called.
    default_top_k: int = 5
    max_top_k: int = 25

    # Rule 5 gate: how strong retrieval must be before generation is attempted.
    min_relevance_score: float = 0.2
    min_evidence_count: int = 1

    # Request-size bounds on client text.
    max_source_chars: int = 200_000
    max_draft_chars: int = 20_000

    # Mock-only: how many status polls a fresh upload spends before it reports
    # ready. 0 keeps local development instant; raise it to exercise Track 3's
    # ingestion-status UI.
    mock_ingestion_delay_polls: int = 0

    # Mock-only: preload the synthetic Ghostbird fixture clients so the demo
    # has evidence without uploading anything first. Off by default so an
    # empty mock is the predictable starting state for tests.
    mock_load_fixtures: bool = False

    # LLM
    llm_provider: LLMProvider = LLMProvider.OPENAI
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_ai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-haiku-latest"
    google_ai_model: str = "gemini-2.0-flash"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Google
    google_service_account_json: str = ""

    # Apify
    apify_api_token: str = ""

    # CRM
    hubspot_api_key: str = ""
    pipedrive_api_token: str = ""

    # Email
    resend_api_key: str = ""
    sendgrid_api_key: str = ""
    email_from: str = "noreply@example.com"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return value
        return []

    @field_validator("api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, value: object) -> object:
        """Accept API_KEYS as a JSON string from the environment."""
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            return json.loads(text)
        return value

    @field_validator("retrieval_backend", mode="before")
    @classmethod
    def parse_retrieval_backend(cls, value: object) -> object:
        if isinstance(value, str):
            return RetrievalBackend(value.lower())
        return value

    @field_validator("llm_provider", mode="before")
    @classmethod
    def parse_llm_provider(cls, value: object) -> LLMProvider:
        if isinstance(value, str):
            return LLMProvider(value.lower())
        return value

    def configured_integrations(self) -> list[str]:
        integrations: list[str] = []
        if self.api_key:
            integrations.append("api_key")
        if self.llm_configured():
            integrations.append("llm")
        if self.supabase_url and self.supabase_service_role_key:
            integrations.append("supabase")
        if self.stripe_secret_key:
            integrations.append("stripe")
        if self.stripe_webhook_secret:
            integrations.append("stripe_webhook")
        if self.google_service_account_json:
            integrations.append("google")
        if self.apify_api_token:
            integrations.append("apify")
        if self.hubspot_api_key:
            integrations.append("hubspot")
        if self.pipedrive_api_token:
            integrations.append("pipedrive")
        if self.resend_api_key:
            integrations.append("resend")
        elif self.sendgrid_api_key:
            integrations.append("sendgrid")
        if self.webhook_secret:
            integrations.append("generic_webhook")
        return integrations

    def client_ids_for_key(self, key: str) -> list[str] | None:
        """Clients this key may reach, or None if the key is not valid.

        An empty ``client_ids`` list on a record means "every client"; so does
        the API_KEY fallback used when no API_KEYS are configured.
        """
        for record in self.api_keys:
            if record.key == key:
                return record.client_ids
        if not self.api_keys and self.api_key and key == self.api_key:
            return []
        return None

    def llm_configured(self) -> bool:
        match self.llm_provider:
            case LLMProvider.OPENAI:
                return bool(self.openai_api_key)
            case LLMProvider.ANTHROPIC:
                return bool(self.anthropic_api_key)
            case LLMProvider.GOOGLE:
                return bool(self.google_ai_api_key)
        return False

    def required_for_action(self, action: str) -> list[str]:
        requirements: dict[str, list[tuple[str, bool]]] = {
            "llm_complete": [
                ("API_KEY", bool(self.api_key)),
                ("LLM provider key", self.llm_configured()),
            ],
            "email_send": [
                ("API_KEY", bool(self.api_key)),
                ("RESEND_API_KEY or SENDGRID_API_KEY", bool(self.resend_api_key or self.sendgrid_api_key)),
                ("EMAIL_FROM", bool(self.email_from)),
            ],
            "apify_run": [
                ("API_KEY", bool(self.api_key)),
                ("APIFY_API_TOKEN", bool(self.apify_api_token)),
            ],
            "google_sheets_append": [
                ("API_KEY", bool(self.api_key)),
                ("GOOGLE_SERVICE_ACCOUNT_JSON", bool(self.google_service_account_json)),
            ],
            "supabase_query": [
                ("API_KEY", bool(self.api_key)),
                ("SUPABASE_URL", bool(self.supabase_url)),
                ("SUPABASE_SERVICE_ROLE_KEY", bool(self.supabase_service_role_key)),
            ],
            "hubspot_contact": [
                ("API_KEY", bool(self.api_key)),
                ("HUBSPOT_API_KEY", bool(self.hubspot_api_key)),
            ],
            "stripe_customer": [
                ("API_KEY", bool(self.api_key)),
                ("STRIPE_SECRET_KEY", bool(self.stripe_secret_key)),
            ],
            "stripe_webhook": [
                ("STRIPE_WEBHOOK_SECRET", bool(self.stripe_webhook_secret)),
            ],
            "generic_webhook": [
                ("WEBHOOK_SECRET", bool(self.webhook_secret)),
            ],
        }
        missing: list[str] = []
        for name, configured in requirements.get(action, []):
            if not configured:
                missing.append(name)
        return missing


@lru_cache
def get_settings() -> Settings:
    return Settings()
