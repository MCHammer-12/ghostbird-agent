import asyncio
import hashlib
from typing import Any, TypeVar

from pydantic import BaseModel

from app.ghostbird.model_runner import StructuredModel
from app.ghostbird.models import (
    AnecdoteCandidate,
    AnecdoteExtraction,
    AgentWriteResult,
    DraftedPost,
    DraftInput,
    EnrichedPost,
    EnrichmentInput,
    IdeationInput,
    IdeationResult,
    IngestionResult,
    IntakeAnalysis,
    MetricCandidate,
    MetricExtraction,
    OutputVerification,
    QuoteCandidate,
    QuoteExtraction,
    ReviewStatus,
    SourceDocument,
    StoredEvidence,
    VoiceProfile,
    VoiceProfileCandidate,
)
from app.ghostbird.repository import EvidenceRepository
from app.integrations.base import IntegrationError


Candidate = TypeVar("Candidate", MetricCandidate, QuoteCandidate, AnecdoteCandidate)

PROMPT_VERSIONS = {
    "intake": "intake-v1",
    "metric": "metric-v1",
    "quote": "quote-v1",
    "anecdote": "anecdote-v1",
    "voice_profile": "voice-profile-v1",
    "enrich_post": "enrich-post-v2",
    "ideate_post": "ideate-post-v4",
    "draft_post": "draft-post-v2",
    "verify_output": "verify-output-v2",
}


class GhostbirdService:
    def __init__(self, model: StructuredModel, repository: EvidenceRepository) -> None:
        self.model = model
        self.repository = repository

    async def ingest(self, source: SourceDocument) -> IngestionResult:
        source = await self.repository.save_source(source)
        try:
            intake = await self.model.run("intake", IntakeAnalysis, {"source": source.model_dump(mode="json")})

            if intake.clarification_questions or intake.relevance == "unclear":
                await self.repository.set_source_status(source.client_id, source.source_id, "needs_clarification")
                return IngestionResult(
                    client_id=source.client_id,
                    source_id=source.source_id,
                    status="needs_clarification",
                    intake=intake,
                )

            if intake.relevance == "irrelevant":
                await self.repository.set_source_status(source.client_id, source.source_id, "ignored")
                return IngestionResult(
                    client_id=source.client_id,
                    source_id=source.source_id,
                    status="ignored",
                    intake=intake,
                )

            writes = await asyncio.gather(
                self._run_metric_agent(source),
                self._run_quote_agent(source),
                self._run_anecdote_agent(source),
            )
            writes.append(await self._run_voice_profile_agent(source))
            await self.repository.set_source_status(source.client_id, source.source_id, "ready")
            return IngestionResult(
                client_id=source.client_id,
                source_id=source.source_id,
                status="ready",
                intake=intake,
                writes=writes,
            )
        except Exception:
            await self.repository.set_source_status(source.client_id, source.source_id, "failed")
            raise

    async def enrich(self, client_id: str, request: EnrichmentInput) -> EnrichedPost:
        evidence = await self.repository.search_evidence(client_id, request.draft_text, 12)
        profile = await self.repository.get_voice_profile(client_id)
        result = await self.model.run(
            "enrich_post",
            EnrichedPost,
            {
                "request": request.model_dump(mode="json"),
                "voice_profile_markdown": profile.markdown if profile else None,
                "evidence": [record.model_dump(mode="json") for record in evidence],
            },
        )
        self._verify_references(result, {record.evidence_id for record in evidence})
        verification = await self._verify_output(result, evidence)
        self._require_valid_output(verification)
        return result.model_copy(update={"verification": verification})

    async def ideate(self, client_id: str, request: IdeationInput) -> IdeationResult:
        query = " ".join(value for value in (request.topic, request.audience, request.goal) if value)
        evidence = await self.repository.search_evidence(client_id, query, 16)
        profile = await self.repository.get_voice_profile(client_id)
        result = await self.model.run(
            "ideate_post",
            IdeationResult,
            {
                "request": request.model_dump(mode="json"),
                "voice_profile_markdown": profile.markdown if profile else None,
                "evidence": [record.model_dump(mode="json") for record in evidence],
            },
        )
        if len(result.ideas) != request.count:
            raise IntegrationError(
                "ghostbird",
                f"Ideation returned {len(result.ideas)} ideas; expected {request.count}",
            )
        allowed = {record.evidence_id for record in evidence}
        evidence_kinds = {record.evidence_id: record.kind for record in evidence}
        for idea in result.ideas:
            self._verify_references(idea, allowed)
            if not any(
                evidence_kinds.get(reference.evidence_id) == idea.basis
                for reference in idea.supporting_evidence
            ):
                raise IntegrationError(
                    "ghostbird",
                    f"Idea basis {idea.basis} has no supporting evidence of that kind",
                )
        verification = await self._verify_output(result, evidence)
        self._require_valid_output(verification)
        return result.model_copy(update={"verification": verification})

    async def draft(self, client_id: str, request: DraftInput) -> DraftedPost:
        evidence = await self.repository.search_evidence(client_id, request.idea, 16)
        profile = await self.repository.get_voice_profile(client_id)
        result = await self.model.run(
            "draft_post",
            DraftedPost,
            {
                "request": request.model_dump(mode="json"),
                "voice_profile_markdown": profile.markdown if profile else None,
                "evidence": [record.model_dump(mode="json") for record in evidence],
            },
        )
        self._verify_references(result, {record.evidence_id for record in evidence})
        verification = await self._verify_output(result, evidence)
        self._require_valid_output(verification)
        return result.model_copy(update={"verification": verification})

    async def _run_metric_agent(self, source: SourceDocument) -> AgentWriteResult:
        extraction = await self.model.run("metric", MetricExtraction, self._source_payload(source))
        records = [self._store_candidate("metric", source, record) for record in extraction.records]
        await self.repository.upsert_metrics(records)
        return AgentWriteResult(agent="metric", records_written=len(records), warnings=extraction.warnings)

    async def _run_quote_agent(self, source: SourceDocument) -> AgentWriteResult:
        extraction = await self.model.run("quote", QuoteExtraction, self._source_payload(source))
        records = [self._store_candidate("quote", source, record) for record in extraction.records]
        await self.repository.upsert_quotes(records)
        return AgentWriteResult(agent="quote", records_written=len(records), warnings=extraction.warnings)

    async def _run_anecdote_agent(self, source: SourceDocument) -> AgentWriteResult:
        extraction = await self.model.run("anecdote", AnecdoteExtraction, self._source_payload(source))
        records = [self._store_candidate("anecdote", source, record) for record in extraction.records]
        await self.repository.upsert_anecdotes(records)
        return AgentWriteResult(agent="anecdote", records_written=len(records), warnings=extraction.warnings)

    async def _run_voice_profile_agent(self, source: SourceDocument) -> AgentWriteResult:
        current = await self.repository.get_voice_profile(source.client_id)
        source_evidence = await self.repository.list_source_evidence(source.client_id, source.source_id)
        candidate = await self.model.run(
            "voice_profile",
            VoiceProfileCandidate,
            self._source_payload(source)
            | {
                "existing_voice_profile_markdown": current.markdown if current and current.markdown else None,
                "source_evidence": [record.model_dump(mode="json") for record in source_evidence],
            },
        )
        allowed_ids = {record.evidence_id for record in source_evidence}
        new_evidence_ids = list(dict.fromkeys(candidate.supporting_evidence_ids))
        invalid = set(new_evidence_ids) - allowed_ids
        if invalid:
            raise IntegrationError("ghostbird", f"Voice profile returned invalid evidence IDs: {sorted(invalid)}")
        uncited = [evidence_id for evidence_id in new_evidence_ids if evidence_id not in candidate.markdown]
        if uncited:
            raise IntegrationError("ghostbird", f"Voice profile omitted evidence IDs from Markdown: {uncited}")
        evidence_ids = list(dict.fromkeys((current.evidence_ids if current else []) + new_evidence_ids))
        profile = VoiceProfile(
            client_id=source.client_id,
            markdown=candidate.markdown,
            evidence_ids=evidence_ids,
            prompt_version=PROMPT_VERSIONS["voice_profile"],
        )
        await self.repository.upsert_voice_profile(profile, current.version if current else None)
        return AgentWriteResult(agent="voice_profile", records_written=1)

    def _store_candidate(
        self,
        kind: str,
        source: SourceDocument,
        candidate: Candidate,
    ) -> StoredEvidence:
        prefix = {"metric": "met", "quote": "quo", "anecdote": "ane"}[kind]
        digest = hashlib.sha256(
            f"{source.client_id}|{source.source_id}|{kind}|{candidate.source_location}|{candidate.excerpt}".encode()
        ).hexdigest()[:32]
        excerpt = candidate.excerpt.strip()
        start = source.text.find(excerpt)
        if start < 0:
            raise IntegrationError(
                "ghostbird",
                f"{kind} evidence excerpt does not occur in the uploaded source",
            )
        end = start + len(excerpt)
        data = candidate.model_dump(mode="json", exclude={
            "excerpt",
            "source_location",
            "scope",
            "confidence",
            "review_status",
        })
        data["claimed_source_location"] = candidate.source_location
        return StoredEvidence(
            evidence_id=f"{prefix}_{digest}",
            client_id=source.client_id,
            source_id=source.source_id,
            kind=kind,
            excerpt=excerpt,
            source_location=f"chars:{start}-{end}",
            scope=candidate.scope,
            confidence=candidate.confidence,
            review_status=ReviewStatus.PROPOSED,
            data=data,
        )

    @staticmethod
    def _source_payload(source: SourceDocument) -> dict[str, Any]:
        return {"source": source.model_dump(mode="json")}

    @staticmethod
    def _verify_references(result: BaseModel, allowed_ids: set[str]) -> None:
        serialized = result.model_dump(mode="json")
        referenced: set[str] = set()

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                if "evidence_id" in value:
                    referenced.add(value["evidence_id"])
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)

        collect(serialized)
        invalid = referenced - allowed_ids
        if invalid:
            raise IntegrationError("ghostbird", f"Model returned invalid evidence IDs: {sorted(invalid)}")

    async def _verify_output(
        self,
        output: BaseModel,
        evidence: list[StoredEvidence],
    ) -> OutputVerification:
        return await self.model.run(
            "verify_output",
            OutputVerification,
            {
                "output": output.model_dump(mode="json", exclude={"verification"}),
                "evidence": [record.model_dump(mode="json") for record in evidence],
            },
        )

    @staticmethod
    def _require_valid_output(verification: OutputVerification) -> None:
        if not verification.valid:
            raise IntegrationError(
                "ghostbird",
                "Output verification failed; content was not returned",
            )
