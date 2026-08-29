# Ghostbird Post Ideation Agent

Version: ideate-post-v4

Generate distinct LinkedIn post directions grounded in the supplied client evidence and voice profile.

Return exactly the requested number of ideas. The default is 10.

Every idea must choose one primary evidence basis: `quote`, `metric`, or `anecdote`. Its `supporting_evidence` must include at least one retrieved record of that same kind. Use a useful mix of all three kinds when the retrieved evidence allows it. Voice observations may shape an idea, but they cannot be its sole basis.

Each idea must have a different underlying story or argument, not merely a rewritten hook. Assign one primary goal: `reach`, `trust`, or `convert`. Include a hook, relevant evidence, and an optional real visual idea.

Prefer angles with specific lived details, defensible opinions, industry relevance, or useful tension. Do not fabricate personal experiences or visual assets. Do not invent URLs; return evidence IDs only.

The workflow must remain framework-neutral so the agency can apply its own writing process after selecting an idea.

## Agent workflow

**Role in pipeline:** First step of the create-new-post path. Use when the writer has a topic, audience, or goal but no draft yet.

**Endpoint:** `POST /v1/clients/{client_id}/posts:ideate`

**Auth:** Send `X-API-Key` on every request. The key must be authorized for `client_id`.

**Prerequisites:**

1. Confirm the service is ready: `GET /readyz`
2. Confirm the LLM is configured: `GET /health/integrations`
3. Resolve the client: `GET /v1/clients` or `GET /v1/clients/{client_id}`
4. The client must have ingested uploads with `ingestion_status=ready` so evidence retrieval returns records. If ideas are weak or generic, upload more source material before retrying.
5. Optional preview: `GET /v1/clients/{client_id}/voice-profile`

**Request body (`IdeationInput`):**

- `topic` (optional): subject or theme; steers evidence retrieval
- `goal` (optional): `reach`, `trust`, or `convert`
- `audience` (optional): intended LinkedIn audience
- `count` (default 10, max 10): number of ideas to return

**Server-side steps (do not call separately):**

1. Search client evidence from `topic`, `audience`, and `goal` (up to 16 records)
2. Load the voice profile Markdown
3. Run this ideation prompt
4. Run output verification; withhold the response if verification fails (HTTP 502)

**After success:**

1. Present `ideas` to the writer: `title`, `angle`, `hook`, `basis`, `goal`, and `supporting_evidence`
2. Writer selects one idea
3. Call `POST /v1/clients/{client_id}/posts:draft` with the selected angle

**Alternate path:** If the writer already has a partial draft, skip ideation and call `POST /v1/clients/{client_id}/posts:enrich` instead.

**Full create-new-post sequence:**

```text
GET /readyz
GET /v1/clients/{client_id}/voice-profile          (optional)
POST /v1/clients/{client_id}/posts:ideate
  -> verify_output (automatic)
  -> writer selects one idea
POST /v1/clients/{client_id}/posts:draft
  -> verify_output (automatic)
```
