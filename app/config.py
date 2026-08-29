"""Application settings."""

from __future__ import annotations

import json
from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COURIER = "courier"


class APIKeyRecord(BaseModel):
    """One API key and the clients it may reach on ghostbird agent routes."""

    key: str
    principal_id: str
    client_ids: list[str] = Field(default_factory=list)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Ghostbird Agent"
    environment: str = "development"
    api_key: str = ""
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    # Ghostbird agent auth: JSON list of {"key", "principal_id", "client_ids"}.
    # When empty, API_KEY above is accepted for every client. NoDecode hands the
    # raw string to parse_api_keys, so a blank API_KEYS= means "unset" rather
    # than a JSON decode error at startup.
    api_keys: Annotated[list[APIKeyRecord], NoDecode] = Field(default_factory=list)

    # LLM
    llm_provider: LLMProvider = LLMProvider.OPENAI
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_ai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-haiku-latest"
    google_ai_model: str = "gemini-2.0-flash"

    # Courier — self-hosted, OpenAI-compatible inference (docs/courier/api.txt).
    courier_base_url: str = ""
    courier_api_key: str = ""
    courier_model: str = ""
    courier_timeout_seconds: float = 300.0
    courier_max_tokens: int = 2048

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            return [origin.strip() for origin in text.split(",") if origin.strip()]
        if isinstance(value, list):
            return value
        return []

    @field_validator("api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            return json.loads(text)
        return value

    @field_validator("llm_provider", mode="before")
    @classmethod
    def parse_llm_provider(cls, value: object) -> LLMProvider:
        if isinstance(value, str):
            return LLMProvider(value.lower())
        return value

    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    def configured_integrations(self) -> list[str]:
        integrations: list[str] = []
        if self.api_key:
            integrations.append("api_key")
        if self.llm_configured():
            integrations.append("llm")
        if self.supabase_configured():
            integrations.append("supabase")
        return integrations

    def client_ids_for_key(self, key: str) -> list[str] | None:
        """Clients this key may reach, or None if the key is not valid."""
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
            case LLMProvider.COURIER:
                return bool(self.courier_api_key and self.courier_base_url and self.courier_model)
        return False

    def courier_endpoint(self, path: str) -> str:
        """Absolute URL for a Courier OpenAI-compatible path."""
        return f"{self.courier_base_url.rstrip('/')}/{path.lstrip('/')}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
