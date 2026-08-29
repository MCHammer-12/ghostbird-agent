"""The Track 1 <-> Track 2 boundary (docs/TRACKS.md, "Required Interface to Track 2").

Track 2 depends on this module and nothing else about the knowledge engine
(Rule 2). It contains three things:

``RetrievalService``
    The contract Track 1 implements and Track 2 calls. Four functions:
    ``ingest_source``, ``get_ingestion_status``, ``search_context``,
    ``get_evidence``. Track 1's tables, chunking, embeddings, and SQL can
    change freely as long as this holds.

``MockRetrievalService``
    An in-memory stand-in backed by the synthetic Ghostbird fixture data, so
    Track 2 and Track 3 can build the whole flow before Track 1 lands
    (Rule 7). Its segmentation and scoring are deliberately naive placeholders
    -- they are *not* Track 1's design. What it does reproduce faithfully,
    because Track 2 and Track 3 test against it: client isolation,
    idempotent uploads, and evidence that is not searchable until its
    ingestion job reports ``ready``.

``retrieve_scoped``
    The Track 2 helper that searches for one client and re-checks the result
    on the way out.

Two reserved dict keys keep the documented signatures intact while carrying
the remaining fields of the shared contracts:

- ``metadata[METADATA_IDEMPOTENCY_KEY]`` carries ``SourceInput.idempotency_key``.
- ``filters[FILTER_TOP_K]``             carries ``SearchRequest.top_k``.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from app.isolation import enforce_client_scope
from app.schemas.evidence import (
    EvidenceCard,
    ExpandedEvidence,
    IngestionJob,
    IngestionStatus,
)

logger = logging.getLogger(__name__)

METADATA_IDEMPOTENCY_KEY = "idempotency_key"
FILTER_TOP_K = "top_k"

#: Fallbacks used when Settings does not carry these knobs.
DEFAULT_TOP_K = 5
MAX_TOP_K = 25

#: Where the synthetic Ghostbird fixture set lives. Override for tests or a
#: different checkout with GHOSTBIRD_FIXTURES_DIR.
FIXTURES_DIR_NAME = "Ghostbird — Synthetic Client Data for Hackathon"


def fixtures_dir() -> Path:
    override = os.environ.get("GHOSTBIRD_FIXTURES_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / FIXTURES_DIR_NAME


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------


@runtime_checkable
class RetrievalService(Protocol):
    """The knowledge engine, as Track 2 sees it."""

    async def ingest_source(
        self,
        client_id: str,
        text: str,
        metadata: dict[str, Any],
    ) -> str:
        """Accept a source for a client and return its ingestion job ID."""
        ...

    async def get_ingestion_status(
        self,
        client_id: str,
        job_id: str,
    ) -> IngestionJob | None:
        """Report a job's status, or None if it does not exist for this client."""
        ...

    async def search_context(
        self,
        client_id: str,
        query: str,
        filters: dict[str, Any],
    ) -> list[EvidenceCard]:
        """Return client-scoped evidence, most relevant first.

        Must never return another client's content, and must never return
        content from an ingestion job that is not ``ready``.
        """
        ...

    async def get_evidence(
        self,
        client_id: str,
        evidence_id: str,
    ) -> ExpandedEvidence | None:
        """Return one evidence record with its surrounding source context."""
        ...


# ---------------------------------------------------------------------------
# Track 2 orchestration
# ---------------------------------------------------------------------------


async def retrieve_scoped(
    service: RetrievalService,
    settings: Any,
    client_id: str,
    query: str,
    filters: dict[str, Any] | None = None,
    top_k: int | None = None,
) -> list[EvidenceCard]:
    """Search Track 1 for one client and verify the result stays in scope.

    Implements the middle of the Track 2 security flow:

        ... -> Call Track 1 -> Validate returned evidence belongs to client -> ...
    """
    default_k = getattr(settings, "default_top_k", DEFAULT_TOP_K)
    max_k = getattr(settings, "max_top_k", MAX_TOP_K)
    resolved_top_k = min(top_k or default_k, max_k)
    merged: dict[str, Any] = {**(filters or {}), FILTER_TOP_K: resolved_top_k}
    cards = await service.search_context(client_id, query, merged)
    return enforce_client_scope(client_id, cards)


# ---------------------------------------------------------------------------
# Mock implementation
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset(
    """a an and are as at be but by for from had has have how i if in into is it
    its of on or that the their they this to was were what when where which who
    will with you your""".split()
)

#: Segments shorter than this are conversational filler, not evidence.
_MIN_SEGMENT_CHARS = 20


def _tokens(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9']+", text.lower())
        if word not in _STOPWORDS and len(word) > 2
    }


def _segment(text: str) -> list[str]:
    """Placeholder segmentation for uploaded text. Track 1 replaces this."""
    parts = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if parts:
        return parts
    return [chunk.strip() for chunk in re.findall(r".{1,600}(?:\s|$)", text) if chunk.strip()]


def _label(excerpt: str) -> str:
    """Placeholder type labelling so Track 3 has varied cards to render."""
    if re.search(r"\d+\s?(%|percent|x\b)|\$\s?\d", excerpt):
        return "metric"
    if '"' in excerpt or "“" in excerpt:
        return "quote"
    return "anecdote"


@dataclass
class _Segment:
    evidence_id: str
    source_id: str
    job_id: str
    index: int
    source_location: str
    excerpt: str
    type: str
    tokens: set[str] = field(default_factory=set)


@dataclass
class _ClientStore:
    jobs: dict[str, IngestionJob] = field(default_factory=dict)
    segments: dict[str, _Segment] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    by_idempotency: dict[str, str] = field(default_factory=dict)
    polls: dict[str, int] = field(default_factory=dict)
    source_count: int = 0


# --- fixture loading -------------------------------------------------------


def _group_utterances(sentences: list[dict[str, Any]]) -> list[str]:
    """Collapse consecutive sentences by the same speaker into one excerpt."""
    grouped: list[str] = []
    speaker: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer and speaker:
            grouped.append(f"{speaker}: {' '.join(buffer)}")

    for sentence in sentences:
        name = str(sentence.get("speaker_name") or "Speaker")
        text = str(sentence.get("text") or "").strip()
        if not text:
            continue
        if name != speaker:
            flush()
            speaker, buffer = name, [text]
        else:
            buffer.append(text)
    flush()
    return [block for block in grouped if len(block) >= _MIN_SEGMENT_CHARS]


def _load_fixture_stores() -> dict[str, _ClientStore]:
    """Build one ready-to-search store per fixture client.

    Returns an empty mapping if the fixture set is not present, so the service
    still starts in a deployment that ships without it.
    """
    root = fixtures_dir()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        logger.warning("Ghostbird fixture data not found at %s", root)
        return {}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stores: dict[str, _ClientStore] = {
        client_id: _ClientStore() for client_id in manifest.get("clients", {})
    }
    interview_counts: dict[str, int] = {}
    thread_counts: dict[str, int] = {}

    def store_for(client_id: str) -> _ClientStore:
        return stores.setdefault(client_id, _ClientStore())

    def add(store: _ClientStore, segment: _Segment) -> None:
        store.segments[segment.evidence_id] = segment
        store.order.append(segment.evidence_id)

    def ready_job(store: _ClientStore, slug: str) -> str:
        job_id = f"job_{slug}"
        store.jobs[job_id] = IngestionJob(
            job_id=job_id, status=IngestionStatus.READY, stage="complete"
        )
        store.source_count += 1
        return job_id

    for entry in manifest.get("transcripts", []):
        path = root / str(entry.get("json_file", ""))
        if not path.is_file():
            logger.warning("fixture transcript missing: %s", path)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        client_id = str(entry.get("client_ref") or data.get("_client_ref") or "")
        if not client_id:
            continue

        store = store_for(client_id)
        slug = str(entry.get("slug") or path.stem)
        source_id = f"src_{slug}"
        job_id = ready_job(store, slug)
        interview_counts[client_id] = interview_counts.get(client_id, 0) + 1
        label = f"Interview {interview_counts[client_id]}"

        index = 0
        summary = str((data.get("summary") or {}).get("short_summary") or "").strip()
        if summary:
            index += 1
            add(
                store,
                _Segment(
                    evidence_id=f"ev_{slug}_{index:02d}",
                    source_id=source_id,
                    job_id=job_id,
                    index=index,
                    source_location=f"{label}, summary",
                    excerpt=summary,
                    type="summary",
                    tokens=_tokens(summary),
                ),
            )

        for excerpt in _group_utterances(data.get("sentences") or []):
            index += 1
            add(
                store,
                _Segment(
                    evidence_id=f"ev_{slug}_{index:02d}",
                    source_id=source_id,
                    job_id=job_id,
                    index=index,
                    source_location=f"{label}, segment {index}",
                    excerpt=excerpt,
                    type=_label(excerpt),
                    tokens=_tokens(excerpt),
                ),
            )

    for entry in manifest.get("email_threads", []):
        path = root / str(entry.get("json_file", ""))
        if not path.is_file():
            logger.warning("fixture email thread missing: %s", path)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        client_id = str(entry.get("client_ref") or data.get("_client_ref") or "")
        if not client_id:
            continue

        store = store_for(client_id)
        slug = str(entry.get("slug") or path.stem)
        source_id = f"src_{slug}"
        job_id = ready_job(store, slug)
        thread_counts[client_id] = thread_counts.get(client_id, 0) + 1
        label = f"Email thread {thread_counts[client_id]}"

        for index, message in enumerate(data.get("messages") or [], start=1):
            body = str(message.get("plaintext_body") or message.get("snippet") or "").strip()
            if len(body) < _MIN_SEGMENT_CHARS:
                continue
            sender = str(message.get("sender") or "unknown")
            excerpt = f"From {sender}:\n{body}"
            add(
                store,
                _Segment(
                    evidence_id=f"ev_{slug}_{index:02d}",
                    source_id=source_id,
                    job_id=job_id,
                    index=index,
                    source_location=f"{label}, message {index}",
                    excerpt=excerpt,
                    type="email",
                    tokens=_tokens(excerpt),
                ),
            )

    logger.info(
        "loaded Ghostbird fixtures: %s",
        {client_id: len(store.order) for client_id, store in stores.items()},
    )
    return stores


@lru_cache(maxsize=1)
def _fixture_blueprint() -> dict[str, _ClientStore]:
    """Parsed once per process; each service instance gets its own copy."""
    return _load_fixture_stores()


def fixture_client_ids() -> list[str]:
    """The client IDs the fixture set provides. Useful for demos and tests."""
    return sorted(_fixture_blueprint())


class MockRetrievalService:
    """Implements :class:`RetrievalService`, backed by the fixture data.

    Starts empty. Pass ``load_fixtures=True`` (or set ``MOCK_LOAD_FIXTURES``)
    to preload the synthetic Ghostbird clients, which is what makes the demo
    work without uploading anything first; an empty store is the default so
    tests have a predictable starting state.

    Preloaded fixture sources are ``ready`` immediately. Sources uploaded at
    runtime go through the same ready-gating an ingestion pipeline would; set
    ``mock_ingestion_delay_polls`` on Settings to make that observable.
    """

    def __init__(self, settings: Any = None, *, load_fixtures: bool | None = None) -> None:
        self._settings = settings
        self._clients: dict[str, _ClientStore] = {}
        self._ids = itertools.count(1)
        self._lock = asyncio.Lock()
        if load_fixtures is None:
            load_fixtures = bool(getattr(settings, "mock_load_fixtures", False))
        if load_fixtures:
            self._preload()

    def _preload(self) -> None:
        for client_id, blueprint in _fixture_blueprint().items():
            store = self._store(client_id)
            store.jobs.update(blueprint.jobs)
            store.segments.update(blueprint.segments)
            store.order.extend(blueprint.order)
            store.source_count += blueprint.source_count

    def _setting(self, name: str, default: int) -> int:
        value = getattr(self._settings, name, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _store(self, client_id: str) -> _ClientStore:
        return self._clients.setdefault(client_id, _ClientStore())

    def _next(self, prefix: str) -> str:
        return f"{prefix}_{next(self._ids):03d}"

    def _is_ready(self, store: _ClientStore, job_id: str) -> bool:
        job = store.jobs.get(job_id)
        return job is not None and job.status is IngestionStatus.READY

    async def ingest_source(
        self,
        client_id: str,
        text: str,
        metadata: dict[str, Any],
    ) -> str:
        async with self._lock:
            store = self._store(client_id)
            key = str(metadata.get(METADATA_IDEMPOTENCY_KEY) or "")
            if key and key in store.by_idempotency:
                return store.by_idempotency[key]

            job_id = self._next("job")
            source_id = self._next("src")
            store.source_count += 1
            label = (
                metadata.get("external_id")
                or f"{metadata.get('source_type', 'source')} {store.source_count}"
            )

            for index, excerpt in enumerate(_segment(text), start=1):
                evidence_id = self._next("ev")
                store.segments[evidence_id] = _Segment(
                    evidence_id=evidence_id,
                    source_id=source_id,
                    job_id=job_id,
                    index=index,
                    source_location=f"{label}, segment {index}",
                    excerpt=excerpt,
                    type=_label(excerpt),
                    tokens=_tokens(excerpt),
                )
                store.order.append(evidence_id)

            delay = max(0, self._setting("mock_ingestion_delay_polls", 0))
            store.jobs[job_id] = IngestionJob(
                job_id=job_id,
                status=IngestionStatus.QUEUED if delay else IngestionStatus.READY,
                stage="queued" if delay else "complete",
            )
            store.polls[job_id] = 0
            if key:
                store.by_idempotency[key] = job_id
            return job_id

    async def get_ingestion_status(
        self,
        client_id: str,
        job_id: str,
    ) -> IngestionJob | None:
        async with self._lock:
            store = self._store(client_id)
            job = store.jobs.get(job_id)
            if job is None:
                return None

            delay = max(0, self._setting("mock_ingestion_delay_polls", 0))
            if delay and job.status is not IngestionStatus.READY:
                store.polls[job_id] += 1
                if store.polls[job_id] > delay:
                    job = IngestionJob(
                        job_id=job_id, status=IngestionStatus.READY, stage="complete"
                    )
                else:
                    job = IngestionJob(
                        job_id=job_id, status=IngestionStatus.PROCESSING, stage="segmenting"
                    )
                store.jobs[job_id] = job
            return job

    async def search_context(
        self,
        client_id: str,
        query: str,
        filters: dict[str, Any],
    ) -> list[EvidenceCard]:
        async with self._lock:
            store = self._store(client_id)
            wanted = _tokens(query)
            requested_type = filters.get("type")

            scored: list[tuple[float, _Segment]] = []
            if wanted:
                for evidence_id in store.order:
                    segment = store.segments[evidence_id]
                    if not self._is_ready(store, segment.job_id):
                        continue
                    if requested_type and segment.type != requested_type:
                        continue
                    overlap = len(wanted & segment.tokens)
                    if not overlap:
                        continue
                    score = round(min(overlap / len(wanted), 1.0), 4)
                    scored.append((score, segment))

            scored.sort(key=lambda pair: (-pair[0], pair[1].evidence_id))
            top_k = int(
                filters.get(FILTER_TOP_K) or self._setting("default_top_k", DEFAULT_TOP_K)
            )
            return [
                EvidenceCard(
                    evidence_id=segment.evidence_id,
                    client_id=client_id,
                    excerpt=segment.excerpt,
                    source_id=segment.source_id,
                    source_location=segment.source_location,
                    type=segment.type,
                    relevance_score=score,
                )
                for score, segment in scored[:top_k]
            ]

    async def get_evidence(
        self,
        client_id: str,
        evidence_id: str,
    ) -> ExpandedEvidence | None:
        async with self._lock:
            store = self._store(client_id)
            segment = store.segments.get(evidence_id)
            if segment is None or not self._is_ready(store, segment.job_id):
                return None

            neighbours = [
                store.segments[other].excerpt
                for other in store.order
                if store.segments[other].source_id == segment.source_id
                and abs(store.segments[other].index - segment.index) <= 1
            ]
            return ExpandedEvidence(
                evidence_id=segment.evidence_id,
                client_id=client_id,
                excerpt=segment.excerpt,
                source_id=segment.source_id,
                source_location=segment.source_location,
                type=segment.type,
                relevance_score=1.0,
                context="\n\n".join(neighbours),
            )
