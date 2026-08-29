import asyncio
import json

from app.config import get_settings
from app.ghostbird.model_runner import ConfiguredStructuredModel
from app.integrations.llm import LLMClient
from evals.marisol.run import evaluate


async def run_live() -> dict:
    settings = get_settings()
    if not settings.llm_configured():
        return {
            "suite": "marisol-v1-live",
            "status": "not_run",
            "reason": "Configure one LLM provider key in .env.",
        }
    model = ConfiguredStructuredModel(LLMClient(settings))
    return await evaluate(model=model, suite_name="marisol-v1-live", repeat_first=False)


def main() -> None:
    result = asyncio.run(run_live())
    print(json.dumps(result, indent=2))
    if result.get("status") == "not_run":
        raise SystemExit(2)
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
