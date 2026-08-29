from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceScope(StrEnum):
    PERSONAL = "personal"
    CLIENT_ASSOCIATED = "client_associated"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class ReviewStatus(StrEnum):
    PROPOSED = "proposed"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"


class SourceDocument(BaseModel):
    client_id: str
    source_id: str
    title: str
    source_type: str
    text: str
    purpose: str | None = None
    captured_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    speaker_map: dict[str, str] = Field(default_factory=dict)


class IntakeAnalysis(BaseModel):
    source_type: str
    purpose: str | None = None
    relevance: Literal["relevant", "partially_relevant", "irrelevant", "unclear"]
    scope: EvidenceScope = EvidenceScope.UNKNOWN
    speakers: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list, max_length=3)
    notes: list[str] = Field(default_factory=list)


class EvidenceCandidate(BaseModel):
    excerpt: str
    source_location: str
    scope: EvidenceScope
    confidence: float = Field(ge=0, le=1)
    review_status: ReviewStatus = ReviewStatus.PROPOSED


class MetricCandidate(EvidenceCandidate):
    metric_type: str
    value_text: str
    normalized_value: float | None = None
    unit: str | None = None
    subject: str
    context: str
    occurred_at: str | None = None


class QuoteCandidate(EvidenceCandidate):
    quote_text: str
    speaker: str
    speaker_type: str
    quote_type: Literal["direct", "paraphrase", "remembered"]
    context: str


class AnecdoteCandidate(EvidenceCandidate):
    summary: str
    full_story: str
    narrator: str
    people: list[str] = Field(default_factory=list)
    occurred_at: str | None = None
    setup: str
    tension: str
    action: str
    outcome: str
    lesson: str | None = None
    related_evidence_hints: list[str] = Field(default_factory=list)


class VoiceProfileCandidate(BaseModel):
    markdown: str
    supporting_locations: list[str]
    confidence: float = Field(ge=0, le=1)


class MetricExtraction(BaseModel):
    records: list[MetricCandidate]
    warnings: list[str] = Field(default_factory=list)


class QuoteExtraction(BaseModel):
    records: list[QuoteCandidate]
    warnings: list[str] = Field(default_factory=list)


class AnecdoteExtraction(BaseModel):
    records: list[AnecdoteCandidate]
    warnings: list[str] = Field(default_factory=list)


class StoredEvidence(BaseModel):
    evidence_id: str
    client_id: str
    source_id: str
    kind: Literal["metric", "quote", "anecdote"]
    excerpt: str
    source_location: str
    scope: EvidenceScope
    confidence: float
    review_status: ReviewStatus
    data: dict[str, Any]


class VoiceProfile(BaseModel):
    client_id: str
    markdown: str
    evidence_ids: list[str]
    prompt_version: str


class AgentWriteResult(BaseModel):
    agent: Literal["metric", "quote", "anecdote", "voice_profile"]
    records_written: int
    warnings: list[str] = Field(default_factory=list)


class IngestionResult(BaseModel):
    client_id: str
    source_id: str
    status: Literal["needs_clarification", "ready"]
    intake: IntakeAnalysis
    writes: list[AgentWriteResult] = Field(default_factory=list)


class EvidenceReference(BaseModel):
    evidence_id: str
    reason: str


class EnrichedPost(BaseModel):
    enriched_post: str
    references: list[EvidenceReference]
    changes: list[str]
    unsupported_suggestions: list[str] = Field(default_factory=list)


class PostIdea(BaseModel):
    title: str
    angle: str
    goal: Literal["reach", "trust", "convert"]
    hook: str
    supporting_evidence: list[EvidenceReference]
    visual_idea: str | None = None


class IdeationResult(BaseModel):
    ideas: list[PostIdea]

