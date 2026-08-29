# Ghostcoded Hackathon — Track Structure

## Purpose

This project is split into three parallel tracks so the team can build independently and integrate quickly.

The final system should:

- Ingest a client transcript.
- Retrieve relevant client evidence.
- Find usable anecdotes from that evidence.
- Review a draft against client context.
- Prevent cross-client data leakage.
- Expose a clean API that the demo/Lovable experience can consume.
- Optionally expose MCP tools after the REST workflow is working.

The architecture is:

```text
Track 3: Demo / Lovable UI
        ↓
Track 2: FastAPI / Generation / Agent Layer
        ↓
Track 1: Data / Ingestion / Retrieval
```

Each track owns a separate layer. Do not bypass these boundaries.

---

# Shared Contracts

Before building, all three tracks should agree on these shared objects and keep them stable.

## 1. SourceInput

Used when a transcript is uploaded.

```json
{
  "client_id": "client-a",
  "text": "Transcript text...",
  "metadata": {
    "source_type": "interview",
    "captured_at": "2026-08-29T12:00:00Z",
    "external_id": "optional-source-id"
  },
  "idempotency_key": "unique-upload-key"
}
```

## 2. EvidenceCard

This is the main object passed from Track 1 → Track 2 → Track 3.

```json
{
  "evidence_id": "ev_123",
  "client_id": "client-a",
  "excerpt": "Relevant transcript excerpt...",
  "source_id": "src_123",
  "source_location": "Interview 1, segment 14",
  "type": "anecdote",
  "relevance_score": 0.91
}
```

Every evidence result must:

- Belong to the requested client.
- Include a stable evidence ID.
- Include enough source information to verify where it came from.
- Be safe to return to Track 3.

## 3. DraftReviewResponse

```json
{
  "supported_claims": [],
  "unsupported_claims": [],
  "suggested_evidence": [],
  "citations": []
}
```

Every client-specific conclusion should point back to real evidence.

---

# Track 1 — Data, Ingestion, and Retrieval

## Purpose

Track 1 builds the knowledge engine.

Its job is to take transcripts, store them safely, break them into useful pieces, create embeddings, and retrieve the most relevant client-specific evidence.

Track 1 does **not** build the public API, UI, generation prompts, or MCP tools.

## Track 1 Owns

- Supabase / Postgres schema.
- Database migrations.
- pgvector configuration.
- Client isolation at the database level.
- Transcript ingestion.
- Transcript chunking / segmentation.
- Embeddings.
- Semantic search.
- Basic lexical / keyword matching.
- Evidence records.
- Source references.
- Ingestion job status.
- Duplicate-ingestion handling.
- Retrieval tests.

## Required Interface to Track 2

Track 2 should not query Track 1's database tables directly.

Track 1 should expose these capabilities through Python/service functions:

```text
ingest_source(client_id, text, metadata) -> job_id

get_ingestion_status(client_id, job_id) -> status

search_context(client_id, query, filters) -> EvidenceCard[]

get_evidence(client_id, evidence_id) -> expanded evidence
```

These functions are the contract between Track 1 and Track 2.

The internal database structure can change without requiring Track 2 to change, as long as this contract remains stable.

## Track 1 Security Rule

Track 1 must prevent cross-client retrieval at the storage/retrieval layer.

A request for Client A must never return:

- Client B transcript text.
- Client B evidence.
- Client B embeddings.
- Client B source IDs.
- Client B cached results.

Client isolation must not rely on prompting an AI model.

## Definition of Done

Track 1 is ready when:

- Two fictional clients can be ingested separately.
- Search returns relevant evidence.
- Every result includes a stable source reference.
- Client A cannot retrieve Client B evidence.
- Duplicate uploads do not create duplicate searchable content.
- Incomplete/failed ingestion jobs are not searchable.

---

# Track 2 — FastAPI, Generation, and Agent Interfaces

## Purpose

Track 2 turns Track 1's knowledge engine into a secure service that Track 3 and Lovable can consume.

Track 2 owns the API contract and the AI reasoning/generation workflows.

Track 2 does **not** own database tables, chunking logic, embeddings, vector search, or UI components.

## Track 2 Owns

- FastAPI application.
- API routes.
- Request validation.
- Authentication.
- Client authorization.
- Safe error responses.
- Request IDs.
- Privacy-safe logging.
- Calling Track 1 services.
- Anecdote generation.
- Draft review.
- Citation validation.
- OpenAPI documentation.
- Sample requests/responses.
- Optional MCP adapter after REST is complete.

## Required REST API

All Track 3 work should use this API.

### Upload transcript

```http
POST /v1/clients/{client_id}/sources
```

Purpose:

- Validate the caller.
- Confirm access to the client.
- Pass the transcript to Track 1.
- Return the ingestion job ID.

---

### Check ingestion status

```http
GET /v1/clients/{client_id}/ingestion-jobs/{job_id}
```

Example response:

```json
{
  "job_id": "job_123",
  "status": "ready",
  "stage": "complete"
}
```

Expected statuses:

```text
queued
processing
ready
failed
```

---

### Search client evidence

```http
POST /v1/clients/{client_id}/search
```

Example request:

```json
{
  "query": "leadership mistakes",
  "filters": {},
  "top_k": 5
}
```

Example response:

```json
{
  "evidence": [
    {
      "evidence_id": "ev_123",
      "client_id": "client-a",
      "excerpt": "I made the mistake of...",
      "source_id": "src_123",
      "source_location": "Interview 1, segment 14",
      "type": "story",
      "relevance_score": 0.91
    }
  ]
}
```

This endpoint returns evidence only. It does not generate a story.

---

### Find an anecdote

```http
POST /v1/clients/{client_id}/anecdotes:search
```

Example request:

```json
{
  "theme": "learning from failure"
}
```

Flow:

```text
Track 3 request
    ↓
Track 2 authorizes client
    ↓
Track 2 calls Track 1 search_context(...)
    ↓
Track 1 returns EvidenceCards
    ↓
Track 2 gives bounded evidence to the model
    ↓
Model structures a real anecdote from that evidence
    ↓
Track 2 validates all evidence IDs
    ↓
Structured response returned
```

Example response:

```json
{
  "anecdotes": [
    {
      "setup": "The client initially...",
      "event": "During the project...",
      "outcome": "They changed their approach...",
      "relevance": "Shows learning through failure.",
      "evidence_ids": ["ev_123", "ev_124"],
      "confidence": 0.88
    }
  ]
}
```

If evidence is weak, return an insufficient-evidence response instead of inventing a story.

---

### Review a draft

```http
POST /v1/clients/{client_id}/drafts:review
```

Example request:

```json
{
  "draft_text": "When I started my first company at 18..."
}
```

Example response:

```json
{
  "supported_claims": [
    {
      "claim": "The client started a company.",
      "evidence_ids": ["ev_201"]
    }
  ],
  "unsupported_claims": [
    {
      "claim": "The client was 18.",
      "reason": "No supporting client evidence was found."
    }
  ],
  "suggested_evidence": [
    {
      "evidence_id": "ev_220",
      "reason": "Relevant story about the client's first customer."
    }
  ],
  "citations": ["ev_201", "ev_220"]
}
```

---

### Open source evidence

```http
GET /v1/clients/{client_id}/evidence/{evidence_id}
```

Purpose:

Allow Track 3 to show the exact supporting transcript context.

Track 2 must verify that the evidence belongs to the requested client before returning it.

---

### Health checks

```http
GET /healthz
GET /readyz
```

`/healthz` means the application is running.

`/readyz` means required dependencies are available.

## Track 2 Security Rule

Track 2 must validate client access **before** calling Track 1.

```text
Authenticate
    ↓
Authorize requested client
    ↓
Call Track 1
    ↓
Validate returned evidence belongs to client
    ↓
Return response
```

Track 2 should never rely on an AI prompt such as:

> Only use Client A.

Authorization must happen in code before retrieval.

## Track 2 Can Start Before Track 1

Track 2 should initially use mocked versions of:

```text
ingest_source(...)
get_ingestion_status(...)
search_context(...)
get_evidence(...)
```

This allows Track 2 to build the API while Track 1 builds the database/retrieval layer.

Later, the mock is replaced with the real Track 1 implementation without changing the API used by Track 3.

## Definition of Done

Track 2 is ready when:

- The service works against mock Track 1 responses.
- It can switch to Track 1's real functions without changing the public API.
- Client authorization happens before retrieval.
- Search returns structured EvidenceCards.
- Anecdotes reference real evidence IDs.
- Draft reviews reference real evidence IDs.
- Weak evidence returns a clear insufficient-evidence result.
- Raw transcripts and API credentials are not written to logs.
- OpenAPI documentation can be handed directly to Track 3/Lovable.

---

# Track 3 — Product Experience, Evaluation, and Demo

## Purpose

Track 3 proves the product solves the ghostwriter's problem.

It builds the demo/Lovable-compatible experience and tests the complete workflow.

Track 3 should only communicate with Track 2's API.

Track 3 should never directly access Supabase or Track 1's internal database.

## Track 3 Owns

- Demo UI.
- Lovable-compatible integration.
- Client selection.
- Transcript upload UI.
- Ingestion-status UI.
- Search/query UI.
- Draft-review UI.
- Anecdote cards.
- Evidence/source display.
- Two fictional client fixtures.
- Demo questions.
- Expected retrieval results.
- End-to-end testing.
- Cross-client leakage tests.
- Unsupported-claim tests.
- Final presentation/demo script.
- Integration instructions.

## Track 3 API Dependency

Track 3 should build against:

```text
POST /v1/clients/{client_id}/sources

GET /v1/clients/{client_id}/ingestion-jobs/{job_id}

POST /v1/clients/{client_id}/search

POST /v1/clients/{client_id}/anecdotes:search

POST /v1/clients/{client_id}/drafts:review

GET /v1/clients/{client_id}/evidence/{evidence_id}
```

Track 3 should not care:

- How transcripts are chunked.
- Which database tables exist.
- Which embedding model is used.
- How vector search works.
- How the AI prompt is constructed.

It only relies on the REST contract above.

## Required Demo Flow

1. Select Client A.
2. Upload Client A transcript.
3. Show ingestion status.
4. Ask for an anecdote related to a post theme.
5. Show the anecdote.
6. Open the supporting evidence.
7. Submit a draft.
8. Show supported and unsupported claims.
9. Switch to Client B.
10. Repeat a Client A query.
11. Demonstrate that Client A evidence is unavailable.
12. Show that the demo/Lovable experience is calling Track 2's API rather than the database directly.

## Definition of Done

Track 3 is ready when:

- The UI works against mocked Track 2 responses initially.
- It can switch to the deployed Track 2 API without changing its UI logic.
- Loading, empty, error, and insufficient-evidence states are handled.
- Evidence can be opened and verified.
- Client isolation is visible in the demo.
- A non-technical stakeholder can understand the system without seeing backend tools.

---

# Ownership Boundaries

| Component | Owner |
|---|---|
| Database schema | Track 1 |
| Database migrations | Track 1 |
| RLS / database isolation | Track 1 |
| Transcript chunking | Track 1 |
| Embeddings | Track 1 |
| Retrieval | Track 1 |
| Evidence records | Track 1 |
| Authentication | Track 2 |
| API authorization | Track 2 |
| FastAPI routes | Track 2 |
| API request/response schemas | Track 2 |
| Anecdote generation | Track 2 |
| Draft review | Track 2 |
| Citation validation | Track 2 |
| MCP adapter | Track 2 |
| Demo / Lovable UI | Track 3 |
| Demo fixtures | Track 3 |
| Expected evaluation results | Track 3 |
| End-to-end testing | Track 3 |
| Presentation/demo | Track 3 |

---

# Team Rules

## Rule 1 — Track 3 never talks directly to Track 1

Correct:

```text
Track 3
   ↓
Track 2
   ↓
Track 1
```

Incorrect:

```text
Track 3
   ↓
Supabase
```

## Rule 2 — Track 2 never depends on Track 1's database structure

Track 2 depends only on:

```text
ingest_source(...)
get_ingestion_status(...)
search_context(...)
get_evidence(...)
```

## Rule 3 — EvidenceCard is the shared evidence format

Track 1 creates it.

Track 2 consumes and returns it.

Track 3 renders it.

If the schema must change, all three tracks agree before changing it.

## Rule 4 — Client ID must be preserved through every layer

```text
Track 3 request
client_id
    ↓
Track 2 authorization
client_id
    ↓
Track 1 retrieval filter
client_id
    ↓
EvidenceCard
client_id
```

## Rule 5 — No AI-generated client facts without evidence

If the model cannot support something with real client evidence:

```text
insufficient evidence
```

is the correct response.

Do not fabricate plausible client stories.

## Rule 6 — Structured JSON over prose

API responses should be predictable objects that the UI can render directly.

Do not make Track 3 parse arbitrary AI prose.

## Rule 7 — Mocks first, integration second

All tracks should be able to build independently.

```text
Track 1 builds retrieval.

Track 2 mocks Track 1.

Track 3 mocks Track 2.
```

Then integrate:

```text
Track 1 → Track 2 → Track 3
```

## Rule 8 — MCP is optional

Do not build MCP until:

- REST API works.
- Track 1 is connected.
- Track 3 is connected.
- Client isolation works.
- Anecdote search works.
- Draft review works.
- Evidence citations work.

If time remains, MCP should wrap the existing Track 2 services rather than duplicate logic.

---

# Final Integration Order

```text
TRACK 1
Knowledge Engine
    │
    │ EvidenceCard / service functions
    ▼
TRACK 2
FastAPI + Generation
    │
    │ REST / OpenAPI
    ▼
TRACK 3
Demo / Lovable
```

Integration should happen in this order:

1. Track 1 → Track 2.
2. Verify search and evidence retrieval.
3. Verify client isolation.
4. Track 2 → Track 3.
5. Verify upload → search → anecdote → evidence → draft review.
6. Run Client A vs Client B isolation test.
7. Fix only demo-blocking or confidentiality-related issues.
8. Rehearse the final demo.

---

# Shared Definition of Success

The project is ready to present when:

- A transcript can be uploaded for a client.
- Ingestion completes successfully.
- A writer can find a useful anecdote.
- That anecdote points to real transcript evidence.
- A draft review identifies supported and unsupported client-specific claims.
- Client A data cannot be retrieved while operating under Client B.
- Track 3 consumes Track 2's API without database access.
- Raw transcripts and credentials are not exposed in logs.
- The team can clearly explain what is hackathon-ready versus what would need production hardening.
