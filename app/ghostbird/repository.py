import hashlib
import re
from collections import defaultdict
from typing import Protocol

from app.ghostbird.models import SourceDocument, StoredEvidence, VoiceProfile
from app.integrations.supabase_ import SupabaseClient


class EvidenceRepository(Protocol):
    async def save_source(self, source: SourceDocument) -> SourceDocument: ...

    async def set_source_status(self, client_id: str, source_id: str, status: str) -> None: ...

    async def upsert_metrics(self, records: list[StoredEvidence]) -> None: ...

    async def upsert_quotes(self, records: list[StoredEvidence]) -> None: ...

    async def upsert_anecdotes(self, records: list[StoredEvidence]) -> None: ...

    async def get_voice_profile(self, client_id: str) -> VoiceProfile | None: ...

    async def upsert_voice_profile(self, profile: VoiceProfile, expected_version: str | None) -> None: ...

    async def list_source_evidence(self, client_id: str, source_id: str) -> list[StoredEvidence]: ...

    async def search_evidence(self, client_id: str, query: str, top_k: int) -> list[StoredEvidence]: ...

    async def get_evidence(self, client_id: str, evidence_id: str) -> StoredEvidence | None: ...


class InMemoryEvidenceRepository:
    def __init__(self) -> None:
        self.sources: dict[tuple[str, str], SourceDocument] = {}
        self.source_status: dict[tuple[str, str], str] = {}
        self.evidence: dict[str, StoredEvidence] = {}
        self.voice_profiles: dict[str, VoiceProfile] = {}
        self.write_counts: dict[str, int] = defaultdict(int)

    async def save_source(self, source: SourceDocument) -> SourceDocument:
        external_id = source.source_id
        digest = hashlib.sha256(f"{source.client_id}|{source.text}".encode()).hexdigest()[:32]
        stored_source = source.model_copy(
            update={
                "source_id": f"upl_{digest}",
                "metadata": source.metadata | {"external_id": external_id},
            }
        )
        for key, existing in self.sources.items():
            if (
                existing.client_id == source.client_id
                and existing.metadata.get("external_id") == external_id
                and existing.source_id != stored_source.source_id
            ):
                self.source_status[key] = "superseded"
        key = (stored_source.client_id, stored_source.source_id)
        self.sources[key] = stored_source
        self.source_status[key] = "processing"
        return stored_source

    async def set_source_status(self, client_id: str, source_id: str, status: str) -> None:
        self.source_status[(client_id, source_id)] = status

    async def upsert_metrics(self, records: list[StoredEvidence]) -> None:
        self._upsert("metric", records)

    async def upsert_quotes(self, records: list[StoredEvidence]) -> None:
        self._upsert("quote", records)

    async def upsert_anecdotes(self, records: list[StoredEvidence]) -> None:
        self._upsert("anecdote", records)

    def _upsert(self, kind: str, records: list[StoredEvidence]) -> None:
        for record in records:
            self.evidence[record.evidence_id] = record
        self.write_counts[kind] += 1

    async def get_voice_profile(self, client_id: str) -> VoiceProfile | None:
        return self.voice_profiles.get(client_id)

    async def upsert_voice_profile(self, profile: VoiceProfile, expected_version: str | None) -> None:
        current = self.voice_profiles.get(profile.client_id)
        current_version = current.version if current else None
        if current_version != expected_version:
            raise RuntimeError("Voice profile changed during generation")
        next_version = str(int(current_version or "0") + 1)
        self.voice_profiles[profile.client_id] = profile.model_copy(update={"version": next_version})
        self.write_counts["voice_profile"] += 1

    async def list_source_evidence(self, client_id: str, source_id: str) -> list[StoredEvidence]:
        return [
            record
            for record in self.evidence.values()
            if record.client_id == client_id and record.source_id == source_id
        ]

    async def search_evidence(self, client_id: str, query: str, top_k: int) -> list[StoredEvidence]:
        terms = {term for term in _terms(query) if len(term) > 2}
        candidates: list[tuple[float, StoredEvidence]] = []
        for record in self.evidence.values():
            if (
                record.client_id != client_id
                or record.review_status == "needs_review"
                or self.source_status.get((record.client_id, record.source_id)) != "ready"
            ):
                continue
            haystack = " ".join((record.excerpt, str(record.data)))
            record_terms = set(_terms(haystack))
            score = len(terms & record_terms) / max(len(terms), 1)
            candidates.append((score, record))
        candidates.sort(key=lambda item: (item[0], item[1].confidence), reverse=True)
        return [record for _, record in candidates[:top_k]]

    async def get_evidence(self, client_id: str, evidence_id: str) -> StoredEvidence | None:
        record = self.evidence.get(evidence_id)
        if (
            record is None
            or record.client_id != client_id
            or record.review_status == "needs_review"
            or self.source_status.get((record.client_id, record.source_id)) != "ready"
        ):
            return None
        return record


class SupabaseEvidenceRepository:
    TABLES = {
        "metric": "metrics",
        "quote": "quotes",
        "anecdote": "anecdotes",
    }

    def __init__(self, client: SupabaseClient) -> None:
        self.client = client

    async def save_source(self, source: SourceDocument) -> SourceDocument:
        content_hash = hashlib.sha256(source.text.encode()).hexdigest()
        rows = await self.client.rpc(
            "start_upload_ingestion",
            {
                "p_client_id": source.client_id,
                "p_external_id": source.source_id,
                "p_title": source.title,
                "p_source_type": source.source_type,
                "p_text": source.text,
                "p_purpose": source.purpose,
                "p_captured_at": source.captured_at,
                "p_metadata": source.metadata | {"speaker_map": source.speaker_map},
                "p_content_hash": content_hash,
            },
        )
        if not rows:
            raise RuntimeError("Supabase did not return the saved upload")
        return source.model_copy(update={"source_id": rows[0]["id"]})

    async def set_source_status(self, client_id: str, source_id: str, status: str) -> None:
        rows = await self.client.update(
            "uploads",
            {"ingestion_status": status},
            {"id": source_id, "client_id": client_id},
        )
        if not rows:
            raise RuntimeError("Supabase did not update the source status")

    async def upsert_metrics(self, records: list[StoredEvidence]) -> None:
        await self._upsert_records("metric", records)

    async def upsert_quotes(self, records: list[StoredEvidence]) -> None:
        await self._upsert_records("quote", records)

    async def upsert_anecdotes(self, records: list[StoredEvidence]) -> None:
        await self._upsert_records("anecdote", records)

    async def _upsert_records(self, kind: str, records: list[StoredEvidence]) -> None:
        if not records:
            return
        rows = []
        for record in records:
            row = {
                "id": record.evidence_id,
                "client_id": record.client_id,
                "upload_id": record.source_id,
                "excerpt": record.excerpt,
                "source_location": record.source_location,
                "scope": record.scope,
                "confidence": record.confidence,
                "review_status": record.review_status,
                **record.data,
            }
            rows.append(row)
        await self.client.upsert(self.TABLES[kind], rows, on_conflict="id")

    async def get_voice_profile(self, client_id: str) -> VoiceProfile | None:
        rows = await self.client.select(
            "clients",
            "id,writing_style,writing_style_prompt_version,updated_at",
            {"id": client_id},
            1,
        )
        if not rows:
            return None
        return VoiceProfile(
            client_id=client_id,
            markdown=rows[0].get("writing_style") or "",
            evidence_ids=_evidence_ids_from_markdown(rows[0].get("writing_style") or ""),
            prompt_version=rows[0].get("writing_style_prompt_version") or "unknown",
            version=rows[0]["updated_at"],
        )

    async def upsert_voice_profile(self, profile: VoiceProfile, expected_version: str | None) -> None:
        filters = {"id": profile.client_id}
        if expected_version is not None:
            filters["updated_at"] = expected_version
        rows = await self.client.update(
            "clients",
            {
                "writing_style": profile.markdown,
                "writing_style_prompt_version": profile.prompt_version,
            },
            filters,
        )
        if not rows:
            raise RuntimeError("Voice profile changed during generation")

    async def list_source_evidence(self, client_id: str, source_id: str) -> list[StoredEvidence]:
        records: list[StoredEvidence] = []
        for kind, table in self.TABLES.items():
            rows = await self.client.select(table, "*", {"client_id": client_id, "upload_id": source_id}, 100)
            records.extend(_rows_to_evidence(kind, rows))
        return records

    async def search_evidence(self, client_id: str, query: str, top_k: int) -> list[StoredEvidence]:
        records: list[StoredEvidence] = []
        for kind, table in self.TABLES.items():
            rows = await self.client.select(
                table,
                "*,uploads!inner(ingestion_status)",
                {"client_id": client_id, "uploads.ingestion_status": "ready"},
                top_k,
            )
            records.extend(_rows_to_evidence(kind, rows))
        query_terms = set(_terms(query))
        records.sort(
            key=lambda record: len(query_terms & set(_terms(record.excerpt))) + record.confidence,
            reverse=True,
        )
        return [record for record in records if record.review_status != "needs_review"][:top_k]

    async def get_evidence(self, client_id: str, evidence_id: str) -> StoredEvidence | None:
        prefix_to_kind = {"met": "metric", "quo": "quote", "ane": "anecdote"}
        kind = prefix_to_kind.get(evidence_id[:3])
        if kind is None:
            return None
        rows = await self.client.select(
            self.TABLES[kind],
            "*,uploads!inner(ingestion_status)",
            {
                "client_id": client_id,
                "id": evidence_id,
                "uploads.ingestion_status": "ready",
            },
            1,
        )
        converted = _rows_to_evidence(kind, rows)
        return converted[0] if converted else None


def _terms(text: str) -> list[str]:
    return ["".join(character for character in word.lower() if character.isalnum()) for word in text.split()]


def _evidence_ids_from_markdown(markdown: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\b(?:met|quo|ane)_[0-9a-f]{32}\b", markdown)))


def _rows_to_evidence(kind: str, rows: list[dict]) -> list[StoredEvidence]:
    shared = {
        "id",
        "client_id",
        "upload_id",
        "excerpt",
        "source_location",
        "scope",
        "confidence",
        "review_status",
        "inserted_at",
        "updated_at",
        "uploads",
    }
    return [
        StoredEvidence(
            evidence_id=row["id"],
            client_id=row["client_id"],
            source_id=row["upload_id"],
            kind=kind,
            excerpt=row["excerpt"],
            source_location=row["source_location"],
            scope=row["scope"],
            confidence=float(row["confidence"]),
            review_status=row["review_status"],
            data={key: value for key, value in row.items() if key not in shared},
        )
        for row in rows
    ]
