from app.config import LLMProvider, Settings
from app.integrations.base import IntegrationError, request_json


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def complete(self, prompt: str, system: str | None = None) -> dict:
        match self.settings.llm_provider:
            case LLMProvider.OPENAI:
                return await self._openai(prompt, system)
            case LLMProvider.ANTHROPIC:
                return await self._anthropic(prompt, system)
            case LLMProvider.GOOGLE:
                return await self._google(prompt, system)
        raise IntegrationError("llm", f"Unsupported provider: {self.settings.llm_provider}")

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
