import unittest
from typing import TypeVar

from pydantic import BaseModel

from app.ghostbird.models import (
    EnrichedPost,
    EnrichmentInput,
    DraftInput,
    EvidenceScope,
    IdeationInput,
    IntakeAnalysis,
    ReviewStatus,
    SourceDocument,
    StoredEvidence,
)
from app.ghostbird.repository import InMemoryEvidenceRepository
from app.ghostbird.service import GhostbirdService
from app.integrations.base import IntegrationError
from app.main import app
from evals.marisol.run import RecordedMarisolModel, evaluate, load_marisol_sources


OutputModel = TypeVar("OutputModel", bound=BaseModel)


class ClarificationModel:
    async def run(
        self,
        prompt_name: str,
        output_model: type[OutputModel],
        payload: dict,
    ) -> OutputModel:
        if prompt_name != "intake":
            raise AssertionError("Extraction should not run before clarification")
        return output_model.model_validate(
            {
                "source_type": "unknown",
                "relevance": "unclear",
                "scope": "unknown",
                "speakers": [],
                "clarification_questions": ["Who is speaking, and how are they related to this client?"],
                "notes": [],
            }
        )


class InvalidReferenceModel(RecordedMarisolModel):
    async def run(
        self,
        prompt_name: str,
        output_model: type[OutputModel],
        payload: dict,
    ) -> OutputModel:
        if prompt_name == "enrich_post":
            return output_model.model_validate(
                {
                    "enriched_post": "A grounded-looking but unsupported post.",
                    "references": [{"evidence_id": "met_not_allowed", "reason": "Unsupported"}],
                    "changes": [],
                    "unsupported_suggestions": [],
                }
            )
        return await super().run(prompt_name, output_model, payload)


class PartialFailureModel(RecordedMarisolModel):
    async def run(
        self,
        prompt_name: str,
        output_model: type[OutputModel],
        payload: dict,
    ) -> OutputModel:
        if prompt_name == "quote":
            raise IntegrationError("llm", "simulated quote failure")
        return await super().run(prompt_name, output_model, payload)


class ValidWritingModel(RecordedMarisolModel):
    async def run(
        self,
        prompt_name: str,
        output_model: type[OutputModel],
        payload: dict,
    ) -> OutputModel:
        if prompt_name == "verify_output":
            return output_model.model_validate({"valid": True, "issues": []})
        evidence_id = payload.get("evidence", [{}])[0].get("evidence_id")
        if prompt_name == "enrich_post":
            return output_model.model_validate(
                {
                    "enriched_post": "Reliability becomes real when the order arrives on time.",
                    "references": [{"evidence_id": evidence_id, "reason": "Client evidence"}],
                    "changes": ["Added a concrete client detail"],
                }
            )
        if prompt_name == "ideate_post":
            count = payload["request"]["count"]
            return output_model.model_validate(
                {
                    "ideas": [
                        {
                            "title": f"Reliability is the strategy {index + 1}",
                            "angle": "Use an operational story to show how trust compounds.",
                            "goal": "trust",
                            "hook": "The sale started a year before the buyer called.",
                            "supporting_evidence": [
                                {"evidence_id": evidence_id, "reason": "Client evidence"}
                            ],
                        }
                        for index in range(count)
                    ]
                }
            )
        if prompt_name == "draft_post":
            return output_model.model_validate(
                {
                    "post": "The sale started a year before the buyer called.",
                    "references": [{"evidence_id": evidence_id, "reason": "Client evidence"}],
                }
            )
        return await super().run(prompt_name, output_model, payload)


class HallucinatedEvidenceModel(RecordedMarisolModel):
    async def run(
        self,
        prompt_name: str,
        output_model: type[OutputModel],
        payload: dict,
    ) -> OutputModel:
        result = await super().run(prompt_name, output_model, payload)
        if prompt_name == "metric":
            result.records[0].excerpt = "This sentence was never in the upload."
        return result


class FailedVerifierModel(ValidWritingModel):
    async def run(
        self,
        prompt_name: str,
        output_model: type[OutputModel],
        payload: dict,
    ) -> OutputModel:
        if prompt_name == "verify_output":
            return output_model.model_validate(
                {
                    "valid": False,
                    "issues": [
                        {
                            "issue_type": "unsupported_claim",
                            "severity": "error",
                            "message": "The output is not supported.",
                            "evidence_ids": [],
                        }
                    ],
                }
            )
        return await super().run(prompt_name, output_model, payload)


class GhostbirdServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_marisol_recorded_evaluation_passes(self) -> None:
        result = await evaluate()
        self.assertEqual([], result["failed"])
        self.assertEqual(1.0, result["score"])

    async def test_ambiguous_source_stops_before_extraction(self) -> None:
        repository = InMemoryEvidenceRepository()
        service = GhostbirdService(ClarificationModel(), repository)
        result = await service.ingest(
            SourceDocument(
                client_id="cli_00000000000000000000000000000001",
                source_id="ambiguous-source",
                title="Imported text",
                source_type="unknown",
                text="A speech with no named speaker or client context.",
            )
        )
        self.assertEqual("needs_clarification", result.status)
        self.assertEqual({}, repository.evidence)
        self.assertEqual(
            "needs_clarification",
            repository.source_status[(result.client_id, result.source_id)],
        )

    async def test_output_rejects_evidence_from_outside_retrieval(self) -> None:
        repository = InMemoryEvidenceRepository()
        service = GhostbirdService(InvalidReferenceModel(), repository)
        await service.ingest(load_marisol_sources()[0])
        with self.assertRaises(IntegrationError):
            await service.enrich(
                "cli_00000000000000000000000000000001",
                EnrichmentInput(draft_text="Reliability matters."),
            )

    async def test_voice_profile_is_one_markdown_value_per_client(self) -> None:
        repository = InMemoryEvidenceRepository()
        service = GhostbirdService(RecordedMarisolModel(), repository)
        sources = load_marisol_sources()
        await service.ingest(sources[0])
        first_markdown = repository.voice_profiles[sources[0].client_id].markdown
        await service.ingest(sources[1])
        second_markdown = repository.voice_profiles[sources[0].client_id].markdown
        self.assertEqual(1, len(repository.voice_profiles))
        self.assertNotEqual(first_markdown, second_markdown)
        self.assertIn("Bad news should be communicated early", second_markdown)

    async def test_partial_extraction_failure_is_not_searchable(self) -> None:
        repository = InMemoryEvidenceRepository()
        service = GhostbirdService(PartialFailureModel(), repository)
        source = load_marisol_sources()[0]
        with self.assertRaises(IntegrationError):
            await service.ingest(source)
        failed_source_id = next(
            stored.source_id
            for stored in repository.sources.values()
            if stored.metadata.get("external_id") == source.source_id
        )
        self.assertEqual("failed", repository.source_status[(source.client_id, failed_source_id)])
        self.assertEqual([], await repository.search_evidence(source.client_id, "revenue", 10))

    async def test_all_writing_flows_are_grounded_and_verified(self) -> None:
        repository = InMemoryEvidenceRepository()
        service = GhostbirdService(ValidWritingModel(), repository)
        source = load_marisol_sources()[0]
        await service.ingest(source)
        enriched = await service.enrich(source.client_id, EnrichmentInput(draft_text="Reliability matters."))
        ideas = await service.ideate(source.client_id, IdeationInput(topic="reliability", goal="trust"))
        draft = await service.draft(
            source.client_id,
            DraftInput(idea=ideas.ideas[0].angle, goal="trust"),
        )
        self.assertTrue(enriched.verification and enriched.verification.valid)
        self.assertTrue(ideas.verification and ideas.verification.valid)
        self.assertTrue(draft.verification and draft.verification.valid)

    async def test_hallucinated_evidence_excerpt_fails_ingestion(self) -> None:
        repository = InMemoryEvidenceRepository()
        service = GhostbirdService(HallucinatedEvidenceModel(), repository)
        source = load_marisol_sources()[0]
        with self.assertRaises(IntegrationError):
            await service.ingest(source)
        self.assertEqual([], await repository.search_evidence(source.client_id, "revenue", 10))

    async def test_failed_output_verification_blocks_delivery(self) -> None:
        repository = InMemoryEvidenceRepository()
        service = GhostbirdService(FailedVerifierModel(), repository)
        source = load_marisol_sources()[0]
        await service.ingest(source)
        with self.assertRaises(IntegrationError):
            await service.enrich(source.client_id, EnrichmentInput(draft_text="Reliability matters."))

    async def test_changed_source_supersedes_old_evidence(self) -> None:
        repository = InMemoryEvidenceRepository()
        client_id = "cli_00000000000000000000000000000001"
        original = await repository.save_source(
            SourceDocument(
                client_id=client_id,
                source_id="external-1",
                title="Version one",
                source_type="notes",
                text="Revenue grew forty percent.",
            )
        )
        await repository.upsert_metrics(
            [
                StoredEvidence(
                    evidence_id="met_00000000000000000000000000000001",
                    client_id=client_id,
                    source_id=original.source_id,
                    kind="metric",
                    excerpt="Revenue grew forty percent.",
                    source_location="chars:0-27",
                    scope=EvidenceScope.PERSONAL,
                    confidence=1,
                    review_status=ReviewStatus.PROPOSED,
                    data={"metric_type": "growth"},
                )
            ]
        )
        await repository.set_source_status(client_id, original.source_id, "ready")
        replacement = await repository.save_source(
            SourceDocument(
                client_id=client_id,
                source_id="external-1",
                title="Version two",
                source_type="notes",
                text="Revenue was flat.",
            )
        )
        await repository.set_source_status(client_id, replacement.source_id, "ready")
        self.assertEqual("superseded", repository.source_status[(client_id, original.source_id)])
        self.assertEqual([], await repository.search_evidence(client_id, "revenue", 10))


class GhostbirdApiContractTests(unittest.TestCase):
    def test_openapi_exposes_v1_workflows(self) -> None:
        paths = app.openapi()["paths"]
        expected = {
            "/v1/clients/{client_id}/sources",
            "/v1/clients/{client_id}/search",
            "/v1/clients/{client_id}/evidence/{evidence_id}",
            "/v1/clients/{client_id}/voice-profile",
            "/v1/clients/{client_id}/posts:enrich",
            "/v1/clients/{client_id}/posts:ideate",
            "/v1/clients/{client_id}/posts:draft",
        }
        self.assertTrue(expected.issubset(paths))


if __name__ == "__main__":
    unittest.main()
