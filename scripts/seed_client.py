"""Seed a client's evidence store by POSTing the synthetic sources to a running server.

Ingestion runs the intake, metric, quote, anecdote, and voice-profile agents against
the configured LLM, so this is slow and it costs tokens -- budget a couple of minutes
per source on a local Courier model.

    uv run python scripts/seed_client.py                     # Marisol, localhost:8000
    uv run python scripts/seed_client.py --client bloom_bar
    uv run python scripts/seed_client.py --base-url https://example.fastapi.app

Without SUPABASE_URL the server keeps evidence in memory, so a restart wipes it and
this has to be re-run.
"""

from __future__ import annotations

import argparse
import sys

import httpx

from app.config import get_settings
from app.ghostbird.synthetic import CLIENT_IDS, load_client_sources

TIMEOUT_SECONDS = 900.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", default="vance_kinder", choices=sorted(CLIENT_IDS))
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--api-key",
        default=None,
        help="Defaults to API_KEY from the environment or .env.",
    )
    parser.add_argument(
        "--client-id",
        default=None,
        help="Override the client ID sources are written under.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = args.api_key or get_settings().api_key
    if not api_key:
        print("No API key. Set API_KEY in .env or pass --api-key.", file=sys.stderr)
        return 1

    client_id = args.client_id or CLIENT_IDS[args.client]
    sources = load_client_sources(args.client, client_id)
    base_url = args.base_url.rstrip("/")
    url = f"{base_url}/v1/clients/{client_id}/sources"
    print(f"Seeding {len(sources)} sources for {args.client} ({client_id}) -> {url}\n")

    failures = 0
    with httpx.Client(timeout=TIMEOUT_SECONDS) as http:
        for index, source in enumerate(sources, start=1):
            label = f"[{index}/{len(sources)}] {source.source_type}: {source.title}"
            print(f"{label} ... ", end="", flush=True)
            try:
                response = http.post(
                    url,
                    headers={"X-API-Key": api_key},
                    json=source.model_dump(mode="json", exclude={"client_id"}),
                )
            except httpx.HTTPError as exc:
                failures += 1
                print(f"request failed: {exc}")
                continue

            if response.status_code >= 400:
                failures += 1
                print(f"HTTP {response.status_code}: {response.text[:300]}")
                continue

            body = response.json()
            writes = ", ".join(
                f"{write['agent']}={write['records_written']}"
                for write in body.get("writes", [])
            )
            print(f"{body['status']}" + (f" ({writes})" if writes else ""))
            for question in body.get("intake", {}).get("clarification_questions", []):
                print(f"    needs clarification: {question}")

    print(f"\nDone. {len(sources) - failures}/{len(sources)} sources ingested.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
