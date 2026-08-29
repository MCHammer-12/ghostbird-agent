"""Pydantic models used for LLM structured-output schema tests."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Anecdote(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class AnecdoteSearchResponse(BaseModel):
    anecdotes: list[Anecdote] = Field(default_factory=list)
    insufficient_evidence: bool = False
    reason: str | None = None


class SupportedClaim(BaseModel):
    claim: str
    evidence_ids: list[str]


class UnsupportedClaim(BaseModel):
    claim: str
    reason: str


class SuggestedEvidence(BaseModel):
    evidence_id: str
    reason: str


class DraftReviewResponse(BaseModel):
    supported_claims: list[SupportedClaim] = Field(default_factory=list)
    unsupported_claims: list[UnsupportedClaim] = Field(default_factory=list)
    suggested_evidence: list[SuggestedEvidence] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
