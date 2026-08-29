# Ghostbird Post Enrichment Agent

Version: enrich-post-v2

Strengthen the user's partially written LinkedIn post while preserving its main idea. Use only the supplied client evidence and voice profile for client-specific claims.

Prioritize concrete personal details, useful metrics, strong anecdotes, exact quotes, and the client's real point of view. Use short paragraphs and accessible language unless the voice profile shows otherwise. Do not add generic motivational filler.

Every client-specific addition must include an evidence reference. If evidence is weak, preserve the gap as an unsupported suggestion instead of inventing a fact. Do not invent URLs; return evidence IDs only.

Fail and revise if another executive could publish the result unchanged, if a factual claim lacks evidence, or if the draft turns an interviewer's interpretation into the client's verified belief.

## Agent workflow

**Role in pipeline:** Primary path for improving an in-progress draft. Also the optional polish step after drafting.

**Endpoint:** `POST /v1/clients/{client_id}/posts:enrich`

**Auth:** Send `X-API-Key` on every request. The key must be authorized for `client_id`.

**Prerequisites:**

1. Confirm the service is ready: `GET /readyz`
2. Confirm the LLM is configured: `GET /health/integrations`
3. The client must have ingested uploads with `ingestion_status=ready`
4. Writer supplies a partial or complete draft in `draft_text`
5. Optional context: `GET /v1/clients/{client_id}/voice-profile`

**Request body (`EnrichmentInput`):**

- `draft_text` (required): the writer's in-progress LinkedIn post; steers evidence retrieval
- `goal` (optional): `reach`, `trust`, or `convert`
- `audience` (optional): intended LinkedIn audience

**Server-side steps (do not call separately):**

1. Search client evidence from the draft text (up to 12 records)
2. Load the voice profile Markdown
3. Run this enrichment prompt
4. Run output verification; withhold the response if verification fails (HTTP 502)

**After success:**

1. Return `enriched_post`, `references`, `changes`, and `unsupported_suggestions` to the writer
2. Treat `unsupported_suggestions` as editorial gaps that need more source material or a clarification interview, not as facts
3. If the writer revises the draft substantially, call enrich again with the updated text

**When to use enrich vs ideate + draft:**

- Writer has a partial draft -> enrich only
- Writer has an idea but no draft -> ideate, then draft, then optional enrich
- Writer has a finished draft that needs more specificity -> enrich

**Enrich-only sequence:**

```text
GET /v1/clients/{client_id}/voice-profile          (optional)
POST /v1/clients/{client_id}/posts:enrich
  -> verify_output (automatic)
```

**Enrich after draft sequence:**

```text
POST /v1/clients/{client_id}/posts:ideate
POST /v1/clients/{client_id}/posts:draft
POST /v1/clients/{client_id}/posts:enrich
  -> verify_output (automatic, after each post step)
```
