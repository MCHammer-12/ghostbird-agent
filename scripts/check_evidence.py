"""Report whether the configured database can actually serve a generation request.

Enrichment and ideation read the evidence tables (metrics/quotes/anecdotes) joined
to uploads with ingestion_status='ready'. Rows in `uploads` alone are invisible to
them, so this prints what each client would really retrieve.

    uv run python scripts/check_evidence.py
"""

from __future__ import annotations

import asyncio
import sys

from app.config import get_settings
from app.dependencies.ghostbird import get_ghostbird_service
from app.ghostbird.repository import _missing_agent_schema


async def main() -> int:
    settings = get_settings()
    if not settings.supabase_configured():
        print("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set.")
        print("The server is using the in-memory store, which starts empty on every restart.")
        return 1

    service = get_ghostbird_service()
    client = service.repository.client
    clients = await client.select("clients", "id,name,writing_style", None, 100)
    try:
        await client.select("metrics", "id", None, 1)
        migrated = True
    except Exception as error:
        if not _missing_agent_schema(error):
            raise
        migrated = False
    if not migrated:
        print(
            "WARNING: the agent evidence migration is not applied "
            "(metrics/quotes/anecdotes are missing).\n"
            "         Retrieval falls back to synthesizing evidence from raw uploads.\n"
        )
    if not clients:
        print("No rows in `clients`.")
        return 1

    print(f"{len(clients)} client(s) in Supabase\n")
    ready = 0
    for record in clients:
        client_id = record["id"]
        try:
            uploads = await client.select(
                "uploads", "id,title,ingestion_status", {"client_id": client_id}, 100
            )
            by_status: dict[str, int] = {}
            for upload in uploads:
                status = upload["ingestion_status"]
                by_status[status] = by_status.get(status, 0) + 1
        except Exception as error:
            if not _missing_agent_schema(error):
                raise
            # Pre-migration: uploads has no ingestion_status column yet.
            uploads = await client.select("uploads", "id", {"client_id": client_id}, 100)
            by_status = {"(pre-migration)": len(uploads)}
        try:
            retrievable = await service.repository.search_evidence(client_id, "", 100)
        except Exception as error:
            if not _missing_agent_schema(error):
                raise
            retrievable = []
        kinds: dict[str, int] = {}
        for evidence in retrievable:
            kinds[evidence.kind] = kinds.get(evidence.kind, 0) + 1

        print(f"  {client_id}  {record.get('name')}")
        print(f"    uploads:        {by_status or 'none'}")
        print(f"    retrievable:    {kinds or 'none'} ({len(retrievable)} records)")
        print(f"    voice profile:  {'yes' if record.get('writing_style') else 'no'}")
        if retrievable:
            ready += 1
            print("    -> can generate")
        else:
            print("    -> CANNOT generate: nothing to cite")
        print()

    print(f"{ready}/{len(clients)} client(s) ready to generate.")
    if not migrated:
        print(
            "\nApply supabase/migrations/20260829220000_add_agent_evidence.sql plus the\n"
            "grants migration, then re-ingest, to replace the upload fallback with real\n"
            "agent-extracted evidence."
        )
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
