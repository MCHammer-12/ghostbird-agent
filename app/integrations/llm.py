import json
import logging
import re

from app.config import LLMProvider, Settings
from app.integrations.base import IntegrationError, request_json

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json_object(content: str) -> dict:
    """Parse the one JSON object a generation prompt asked for.

    Models wrap JSON in markdown fences or a sentence of preamble often enough
    that it is not worth failing the request over. A response that still will
    not parse yields an empty dict: downstream, that becomes an
    insufficient-evidence result, which is the correct Ghostbird answer
    (docs/TRACKS.md, Rule 5) rather than an invented story.
    """
    text = _FENCE.sub("", (content or "").strip()).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            logger.warning("LLM response contained no JSON object")
            return {}
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            # Never log the body: it echoes client source text.
            logger.warning("LLM response was not valid JSON")
            return {}
    return parsed if isinstance(parsed, dict) else {}


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def complete(self, prompt: str, system: str | None = None) -> dict:
        if not self.settings.llm_configured():
            # Checked here rather than at dependency-resolution time so route
            # validation (empty draft, oversized body) still answers first.
            raise IntegrationError(
                "llm",
                f"provider not configured: {self.settings.llm_provider.value}",
                status_code=503,
            )
        match self.settings.llm_provider:
            case LLMProvider.OPENAI:
                return await self._openai(prompt, system)
            case LLMProvider.ANTHROPIC:
                return await self._anthropic(prompt, system)
            case LLMProvider.GOOGLE:
                return await self._google(prompt, system)
        raise IntegrationError("llm", f"Unsupported provider: {self.settings.llm_provider}")

    async def complete_json(self, system: str, prompt: str) -> dict:
        """Run a completion whose prompt requires a single JSON object back.

        Reuses complete(); only the parsing is new.
        """
        result = await self.complete(prompt, system)
        return _extract_json_object(result.get("content", ""))

    async def _openai(self, prompt: str, system: str | None) -> dict:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        data = await request_json(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            service="openai",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.settings.openai_model, "messages": messages},
        )
        content = data["choices"][0]["message"]["content"]
        return {"provider": "openai", "model": self.settings.openai_model, "content": content}

    async def _anthropic(self, prompt: str, system: str | None) -> dict:
        payload: dict = {
            "model": self.settings.anthropic_model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        data = await request_json(
            "POST",
            "https://api.anthropic.com/v1/messages",
            service="anthropic",
            headers={
                "x-api-key": self.settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        content = data["content"][0]["text"]
        return {"provider": "anthropic", "model": self.settings.anthropic_model, "content": content}

    async def _google(self, prompt: str, system: str | None) -> dict:
        contents = [{"parts": [{"text": prompt}]}]
        payload: dict = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.google_ai_model}:generateContent?key={self.settings.google_ai_api_key}"
        )
        data = await request_json("POST", url, service="google_ai", json=payload)
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return {"provider": "google", "model": self.settings.google_ai_model, "content": content}
