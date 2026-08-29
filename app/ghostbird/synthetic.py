"""Loader for the bundled synthetic client dataset.

Every record in that directory is fictional (see its README). It is the only
client material in the repo, so it backs both the eval suite and the local seed
script — keeping one loader here stops the two from drifting apart and breaking
the excerpt-offset checks the eval gold file depends on.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ghostbird.models import SourceDocument

DATA_DIR = (
    Path(__file__).resolve().parents[2] / "Ghostbird — Synthetic Client Data for Hackathon"
)

# The dataset slugs are not valid client IDs (the schema constrains them to
# ^cli_[0-9a-f]{32}$), so map each slug to the row it corresponds to. These match
# the dbId values the demo UI uses in app/static/app.js; override with
# --client-id when seeding a different database.
CLIENT_IDS = {
    "vance_kinder": "cli_927fa9c0e2db4ce4b675505eca2a9fa2",
    "bloom_bar": "cli_3184cf91aced4843a660ae57d0dbd92e",
    "ridgeline": "cli_7499c9e69fc44d43b33df7287a9f7971",
}


def load_manifest(data_dir: Path = DATA_DIR) -> dict:
    return json.loads((data_dir / "manifest.json").read_text())


def load_client_sources(
    slug: str,
    client_id: str | None = None,
    data_dir: Path = DATA_DIR,
) -> list[SourceDocument]:
    """Every transcript then every email thread belonging to one dataset client."""
    if slug not in CLIENT_IDS:
        raise ValueError(f"Unknown client slug: {slug}")
    manifest = load_manifest(data_dir)
    entries = [
        entry
        for group in ("transcripts", "email_threads")
        for entry in manifest[group]
        if entry["client_ref"] == slug
    ]
    return [
        load_source(data_dir / entry["json_file"], client_id or CLIENT_IDS[slug])
        for entry in entries
    ]


def load_source(path: Path, client_id: str) -> SourceDocument:
    data = json.loads(path.read_text())
    if "sentences" in data:
        text = "\n".join(
            f"[{sentence['start_time']:.2f}-{sentence['end_time']:.2f}] "
            f"{sentence['speaker_name']}: {sentence['text']}"
            for sentence in data["sentences"]
        )
        return SourceDocument(
            client_id=client_id,
            source_id=data["id"],
            title=data["title"],
            source_type="call_transcript",
            text=text,
            purpose="Monthly Ghostbird content interview",
            captured_at=data["dateString"],
            metadata={"synthetic": True, "meeting_link": data["meetingLink"]},
        )

    text = "\n\n".join(
        f"[{message['date']}] {message['sender']}:\n{message['plaintext_body']}"
        for message in data["messages"]
    )
    return SourceDocument(
        client_id=client_id,
        source_id=data["threadId"],
        title=data["subject"],
        source_type="email_thread",
        text=text,
        purpose="Client communication",
        captured_at=data["messages"][0]["date"],
        metadata={"synthetic": True},
    )
