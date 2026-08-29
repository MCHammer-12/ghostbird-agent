import asyncio
import copy
import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.ghostbird.models import SourceDocument
from app.ghostbird.model_runner import StructuredModel
from app.ghostbird.repository import InMemoryEvidenceRepository
from app.ghostbird.service import GhostbirdService


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "Ghostbird — Synthetic Client Data for Hackathon"
FIXTURE_DIR = ROOT / "evals" / "marisol"
MARISOL_CLIENT_ID = "cli_00000000000000000000000000000001"
OutputModel = TypeVar("OutputModel", bound=BaseModel)


class RecordedMarisolModel:
    def __init__(self) -> None:
        self.outputs = json.loads((FIXTURE_DIR / "agent_outputs.json").read_text())

    async def run(
        self,
        prompt_name: str,
        output_model: type[OutputModel],
        payload: dict,
    ) -> OutputModel:
        source_id = payload["source"]["metadata"].get("external_id", payload["source"]["source_id"])
        output = copy.deepcopy(self.outputs[source_id][prompt_name])
        if prompt_name == "voice_profile":
            by_location = {
                record["data"]["claimed_source_location"]: record["evidence_id"]
                for record in payload["source_evidence"]
            }
            locations = output.pop("supporting_locations")
            output["supporting_evidence_ids"] = [
                by_location[location] for location in locations if location in by_location
            ]
            for location, evidence_id in by_location.items():
                output["markdown"] = output["markdown"].replace(
                    f"- {location}",
                    f"- {evidence_id} — {location}",
                )
        return output_model.model_validate(output)


def load_marisol_sources() -> list[SourceDocument]:
    paths = [
        DATA_DIR / "transcripts" / "vance_kinder_call_1.json",
        DATA_DIR / "transcripts" / "vance_kinder_call_2.json",
        DATA_DIR / "emails" / "vance_kinder_thread_1.json",
        DATA_DIR / "emails" / "vance_kinder_thread_2.json",
    ]
    return [_load_source(path) for path in paths]


def _load_source(path: Path) -> SourceDocument:
    data = json.loads(path.read_text())
    if "sentences" in data:
        text = "\n".join(
            f"[{sentence['start_time']:.2f}-{sentence['end_time']:.2f}] "
            f"{sentence['speaker_name']}: {sentence['text']}"
            for sentence in data["sentences"]
        )
        return SourceDocument(
            client_id=MARISOL_CLIENT_ID,
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
        client_id=MARISOL_CLIENT_ID,
        source_id=data["threadId"],
        title=data["subject"],
        source_type="email_thread",
        text=text,
        purpose="Client communication",
        captured_at=data["messages"][0]["date"],
        metadata={"synthetic": True},
    )


async def evaluate(
    model: StructuredModel | None = None,
    suite_name: str = "marisol-v1-recorded",
    repeat_first: bool = True,
) -> dict:
    gold = json.loads((FIXTURE_DIR / "gold.json").read_text())
    repository = InMemoryEvidenceRepository()
    service = GhostbirdService(model or RecordedMarisolModel(), repository)
    sources = load_marisol_sources()

    results = []
    results.append(await service.ingest(sources[0]))
    first_count = len(repository.evidence)
    if repeat_first:
        await service.ingest(sources[0])
    duplicate_safe = not repeat_first or len(repository.evidence) == first_count
    for source in sources[1:]:
        results.append(await service.ingest(source))

    checks: list[tuple[str, bool]] = []
    actual_statuses = {
        source.source_id: result.status for source, result in zip(sources, results, strict=True)
    }
    for source_id, status in gold["expected_statuses"].items():
        checks.append((f"status:{source_id}", actual_statuses.get(source_id) == status))

    source_text = {source.source_id: source.text for source in repository.sources.values()}
    for record in repository.evidence.values():
        checks.append((f"exact_excerpt:{record.evidence_id}", record.excerpt in source_text[record.source_id]))

    metrics = {
        (record.data["metric_type"], record.data["value_text"])
        for record in repository.evidence.values()
        if record.kind == "metric"
    }
    for expected in gold["required_metrics"]:
        checks.append((f"metric:{expected[0]}:{expected[1]}", tuple(expected) in metrics))

    quotes = "\n".join(
        record.data["quote_text"]
        for record in repository.evidence.values()
        if record.kind == "quote"
    )
    for fragment in gold["required_quote_fragments"]:
        checks.append((f"quote:{fragment}", fragment in quotes))

    anecdotes = "\n".join(
        f"{record.data['summary']} {record.data['full_story']}"
        for record in repository.evidence.values()
        if record.kind == "anecdote"
    )
    for terms in gold["required_anecdote_terms"]:
        checks.append((f"anecdote:{terms[0]}", all(term in anecdotes for term in terms)))

    profile = await repository.get_voice_profile(MARISOL_CLIENT_ID)
    for term in gold["required_voice_terms"]:
        checks.append((f"voice:{term}", profile is not None and term in profile.markdown))

    checks.extend(
        [
            ("idempotent_reprocessing", duplicate_safe),
            ("single_voice_profile_cell", len(repository.voice_profiles) == 1),
            (
                "irrelevant_source_has_no_evidence",
                not any(
                    repository.sources[(record.client_id, record.source_id)].metadata.get("external_id")
                    == "SYNTHREAD0002"
                    for record in repository.evidence.values()
                ),
            ),
            (
                "cross_client_isolation",
                not await repository.search_evidence(
                    "cli_99999999999999999999999999999999",
                    "revenue",
                    10,
                ),
            ),
        ]
    )

    failed = [name for name, passed in checks if not passed]
    return {
        "suite": suite_name,
        "passed": len(checks) - len(failed),
        "total": len(checks),
        "score": round((len(checks) - len(failed)) / len(checks), 3),
        "failed": failed,
        "evidence_counts": {
            kind: sum(record.kind == kind for record in repository.evidence.values())
            for kind in ("metric", "quote", "anecdote")
        },
    }


def main() -> None:
    result = asyncio.run(evaluate())
    print(json.dumps(result, indent=2))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
