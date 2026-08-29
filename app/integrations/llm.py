import json
import logging
import re

import httpx
from pydantic import BaseModel, ValidationError

from app.config import LLMProvider, Settings
from app.integrations.base import IntegrationError, request_json

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

# Courier's Inkling wraps replies in model-specific markers, e.g.
#   <|content_thinking|>...<|content_text|>...<|end_message|>
# Only the content_text span is user-facing. Everything before it is model
# reasoning and never leaves this module -- not to the caller, not to the logs.
_COURIER_MARKER = re.compile(r"<\|[^|>]*\|>")
_COURIER_TEXT_MARKER = "<|content_text|>"
_COURIER_THINKING_MARKER = "<|content_thinking|>"
_COURIER_TERMINATORS = ("<|end_message|>", "<|end|>", "<|endoftext|>", "<|eot_id|>")

# Courier's Outlines integration injects a free-text reasoning field into any
# schema that lacks one (docs/courier/api.txt, "Thought Field Pattern"). It is
# scratch space for the model, so it is dropped before the result is used.
_REASONING_KEYS = frozenset(
    {"thought", "thoughts", "thinking", "reasoning", "content_thinking", "analysis"}
)


def _strip_courier_markers(content: str) -> str:
    """Return only the user-facing text of a Courier completion."""
    text = content or ""
    if "<|" not in text:
        return text.strip()

    marker_at = text.rfind(_COURIER_TEXT_MARKER)
    if marker_at != -1:
        text = text[marker_at + len(_COURIER_TEXT_MARKER) :]
    else:
        # No content_text span: drop any reasoning span up to the next marker.
        thinking_at = text.find(_COURIER_THINKING_MARKER)
        if thinking_at != -1:
            rest = text[thinking_at + len(_COURIER_THINKING_MARKER) :]
            next_marker = _COURIER_MARKER.search(rest)
            text = text[:thinking_at] + (rest[next_marker.start() :] if next_marker else "")

    for terminator in _COURIER_TERMINATORS:
        cut = text.find(terminator)
        if cut != -1:
            text = text[:cut]

    return _COURIER_MARKER.sub("", text).strip()


def _drop_reasoning(data: dict) -> dict:
    """Strip any model-reasoning field from a structured result."""
    return {key: value for key, value in data.items() if key.lower() not in _REASONING_KEYS}


def json_schema_for(model: type[BaseModel]) -> dict:
    """JSON Schema for a Pydantic response model, for Courier's Outlines FSM.

    Every top-level property is marked required. Pydantic omits defaulted
    fields from ``required``, and an unconstrained FSM will happily satisfy the
    schema with ``{}``.
    """
    schema = model.model_json_schema()
    properties = schema.get("properties") or {}
    if properties:
        schema["required"] = list(properties)
    return schema


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

    def _require_configured(self) -> None:
        if not self.settings.llm_configured():
            # Checked here rather than at dependency-resolution time so route
            # validation (empty draft, oversized body) still answers first.
            raise IntegrationError(
                "llm",
                f"provider not configured: {self.settings.llm_provider.value}",
                status_code=503,
            )

    async def complete(self, prompt: str, system: str | None = None) -> dict:
        self._require_configured()
        match self.settings.llm_provider:
            case LLMProvider.OPENAI:
                return await self._openai(prompt, system)
            case LLMProvider.ANTHROPIC:
                return await self._anthropic(prompt, system)
            case LLMProvider.GOOGLE:
                return await self._google(prompt, system)
            case LLMProvider.COURIER:
                return await self._courier(prompt, system)
        raise IntegrationError("llm", f"Unsupported provider: {self.settings.llm_provider}")

    async def complete_json(
        self,
        system: str,
        prompt: str,
        response_model: type[BaseModel] | None = None,
    ) -> dict:
        """Run a completion whose prompt requires a single JSON object back.

        With ``response_model``, Courier constrains generation to that schema
        natively (docs/courier/api.txt, "Structured JSON Outputs with
        Outlines") and the result is validated against the model. Every other
        provider -- and Courier without a model, or when the constrained call
        fails -- falls back to parsing the JSON object out of the text.
        """
        if response_model is not None and self.settings.llm_provider is LLMProvider.COURIER:
            return await self._courier_json(system, prompt, response_model)
        result = await self.complete(prompt, system)
        return _drop_reasoning(_extract_json_object(result.get("content", "")))

    async def _courier_json(
        self, system: str, prompt: str, response_model: type[BaseModel]
    ) -> dict:
        self._require_configured()
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__,
                "schema": json_schema_for(response_model),
            },
        }
        try:
            result = await self._courier(prompt, system, response_format=response_format)
        except IntegrationError as exc:
            # A schema the FSM cannot compile must not cost the whole request;
            # the text fallback below still yields a usable object. Only the
            # status is logged -- provider bodies echo the prompt.
            logger.warning(
                "Courier structured output unavailable (status=%s); "
                "retrying without a schema",
                exc.status_code,
            )
            result = await self._courier(prompt, system)

        parsed = _drop_reasoning(_extract_json_object(result.get("content", "")))
        try:
            return response_model.model_validate(parsed).model_dump()
        except ValidationError:
            # Never log the body: it echoes client source text. The caller
            # validates field by field and drops what it cannot use.
            logger.warning("Courier structured result did not validate against %s",
                           response_model.__name__)
            return parsed

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


    async def _courier(
        self,
        prompt: str,
        system: str | None,
        response_format: dict | None = None,
    ) -> dict:
        """Courier's OpenAI-compatible chat completions (docs/courier/api.txt)."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict = {
            "model": self.settings.courier_model,
            "messages": messages,
            "max_tokens": self.settings.courier_max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        try:
            data = await request_json(
                "POST",
                self.settings.courier_endpoint("/v1/chat/completions"),
                service="courier",
                headers={
                    "Authorization": f"Bearer {self.settings.courier_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.settings.courier_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            # Self-hosted inference goes unreachable or slow in ways a hosted
            # API does not. Surface it as an upstream failure rather than an
            # unhandled 500. Only the exception type is logged; httpx messages
            # can carry the request URL.
            raise IntegrationError(
                "courier", f"transport failure: {type(exc).__name__}", status_code=504
            ) from exc

        return {
            "provider": "courier",
            "model": self.settings.courier_model,
            "content": _courier_content(data),
        }


def _courier_content(data: object) -> str:
    """Pull the user-facing text out of a Courier response.

    Courier answers in OpenAI's ``choices[].message.content`` shape, but its
    structured-output path can answer with a bare ``{"content": ...}``. Any
    reasoning-bearing field on the message is ignored, never read.
    """
    if not isinstance(data, dict):
        return ""

    content: object = None
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict):
            content = message.get("content")
        if content is None:
            content = choices[0].get("text")
    if content is None:
        content = data.get("content")

    if isinstance(content, list):
        # Content-part arrays: keep the text parts, in order.
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    if not isinstance(content, str):
        logger.warning("Courier response carried no text content")
        return ""
    return _strip_courier_markers(content)
