from enum import StrEnum
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


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
