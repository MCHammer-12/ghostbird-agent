# MCP and agent prompt guide

Research completed August 29, 2026 using the official MCP, OpenAI, and Anthropic documentation.

## Boundary

MCP defines contracts for tools, prompts, and resources. It does not prescribe the internal system prompts for Ghostbird's extraction agents.

Use model prompts for extraction judgment. Use typed tool contracts around retrieval, clarification, validation, and persistence.

## Recommended orchestration

```text
classify upload
  -> clarify if material ambiguity remains
  -> run metric, quote, anecdote, and voice extractors
  -> validate, link, and deduplicate
  -> persist one evidence batch
```

Extractors are read-only and return proposed records. They do not write directly to the database. Only the orchestrator receives the persistence tool.

## Specialist prompt contract

Each specialist prompt should define:

1. One owned outcome.
2. The trust boundary: uploaded content is evidence, never instructions.
3. Precise include and exclude rules.
4. The exact source evidence required for every record.
5. Uncertainty behavior: return `unknown` or request clarification rather than guessing.
6. A stopping rule.
7. A structured output schema.

Keep instructions short and enforce valid output through the schema rather than describing JSON in prose.

## Suggested tool surface

- `ghostbird.classify_upload`
- `ghostbird.extract_metrics`
- `ghostbird.extract_quotes`
- `ghostbird.extract_anecdotes`
- `ghostbird.observe_voice`
- `ghostbird.link_extractions`
- `ghostbird.persist_evidence_batch`
- `ghostbird.retrieve_evidence`

Writer agents should receive read-only retrieval tools. Extraction agents should not receive persistence, external-action, or cross-client tools.

## Shared extraction envelope

```json
{
  "source_id": "source_123",
  "records": [],
  "warnings": [],
  "needs_clarification": false,
  "clarification_fields": [],
  "prompt_version": "metric-v3",
  "schema_version": "1.0"
}
```

Each proposed record should include:

- Source and segment identifiers
- Page, timestamp, or character offsets
- Exact supporting excerpt
- Speaker or subject identity, with `unknown` allowed
- Relationship to client: `personal`, `client_associated`, `external`, or `unknown`
- Confidence
- Extraction reason
- Source hash, prompt version, and schema version

Return identifiers and compact excerpts rather than entire documents.

## Clarification rule

- Continue without interruption when metadata is clear.
- Store `unknown` when uncertainty does not affect provenance or usability.
- Ask one compact batch of questions when uncertainty could create false attribution, client contamination, or misuse.
- Keep unanswered records in `pending_review` and out of normal writer retrieval.

Important clarification fields include purpose, relationship to client, primary speaker, authorship or endorsement, approximate date, and personal versus external evidence.

## Injection boundary

- Treat transcripts, articles, posts, OCR, and other uploaded material as untrusted data.
- Never insert uploaded text into system or developer instructions.
- Label its origin and pass it as user content or tool-result data.
- Ignore instructions contained inside source material.
- Validate every proposed record before persistence.
- Include adversarial uploaded documents in the synthetic evaluation set.

## Retry and duplicate policy

Use an idempotency key such as:

```text
client_id + source_hash + agent_type + prompt_version + schema_version
```

- Retry transient provider or network failures at most twice.
- Allow one correction attempt for schema-validation errors.
- Do not blindly retry database writes.
- Upsert using stable record fingerprints.
- Track attempted, completed, skipped, and failed stages.

## Evaluation

Use the synthetic corpus as a labeled answer set. Measure extraction precision, normalized metric accuracy, exact quote and speaker attribution, anecdote boundaries, voice-observation evidence, personal versus external classification, unnecessary clarification rate, duplicates, unsupported post claims, evidence coverage, prompt-injection resistance, and cross-client leakage.

Keep the prompt, schema, model, and dataset versions fixed during a comparison. Change one variable per experiment.

## Primary sources

- [MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [MCP elicitation specification](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- [OpenAI agent orchestration](https://developers.openai.com/api/docs/guides/agents/orchestration)
- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI agent safety](https://developers.openai.com/api/docs/guides/agent-builder-safety)
- [OpenAI agent evaluations](https://developers.openai.com/api/docs/guides/agent-evals)
- [Anthropic tool definitions](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)
- [Anthropic prompt-injection guidance](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks)
