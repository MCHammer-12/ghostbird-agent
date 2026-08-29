from functools import lru_cache
from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parent / "prompt_text"


@lru_cache
def load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.is_file():
        raise ValueError(f"Unknown Ghostbird prompt: {name}")
    return path.read_text(encoding="utf-8")

