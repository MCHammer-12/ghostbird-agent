# Ghostbird Agent

Ghostbird is a client-isolated context system for evidence-backed LinkedIn ghostwriting. It helps writers either turn a partial post into a stronger, more credible draft or develop a new post from an idea and a client's existing context.

## Product goal

Client interviews, notes, transcripts, and prior posts contain the details that make ghostwritten content sound real: stories, phrasing, numbers, opinions, and intent. Ghostbird turns that material into traceable, client-specific context that a writer can use without manually reviewing every source.

The system must never mix information across clients. Every client-specific fact used in a response should be tied to source evidence that a writer can inspect.

## Writer workflows

### 1. Enrich a partial post

A writer submits an in-progress LinkedIn post and selects a client. Ghostbird retrieves relevant client context and suggests material that can make the draft more specific and authentic:

- Metrics and numbers
- Anecdotes and stories
- Client, external, or interview quotes
- Client interactions and concrete examples
- Images or visual references
- Voice, phrasing, and writing-style cues

The response distinguishes sourced evidence from generated editorial suggestions and includes citations back to the underlying source material.

### 2. Create a new post

A writer starts with an idea, goal, industry, client, target audience, and writing style. Ghostbird retrieves the right context and helps create a grounded post or brief. The workflow can use existing system prompts and focused sub-agent prompts, while keeping client facts limited to retrieved evidence.

## Core product capabilities

1. **Client lookup and selection** - Find a client by name or ID and enforce the selected client as the retrieval boundary.
2. **Ingestion** - Accept uploaded or pasted source material, starting with text and text files. Preserve source, date, speaker, and other useful metadata.
3. **Knowledge extraction** - Segment source material and extract reusable structured context:
   - Metrics
   - Quotes, including text and speaker
   - Anecdotes and stories
   - Opinions and voice cues
   - Images and image metadata
   - Client, date, source, and supporting context
4. **Evidence retrieval** - Retrieve relevant, compact source excerpts for a client and task; do not return an entire transcript by default.
5. **Chat and creation** - Let writers converse with the system to find evidence, generate a brief, enrich a draft, or create a new post.
6. **Client context stores** - Maintain a reusable context store per client. A client-specific repository may be useful for supplemental material, but the authoritative boundary should be enforced in the application database and service layer.

## System design

The initial architecture is API-first:

- **FastAPI service** for deterministic ingestion, retrieval, and draft-review workflows.
- **Supabase Postgres with pgvector** for client-scoped data, metadata, and semantic retrieval.
- **One shared retrieval core** for ingestion, authorization, retrieval, audit, and generation grounding.
- **REST API first** for the app integration; add a thin MCP adapter later for agent-based experiences without duplicating business logic.
- **Asynchronous ingestion jobs** to validate, normalize, segment, enrich, embed, and atomically publish new sources.

## Data model

All tables include `inserted_at` and `updated_at` timestamps.

### clients

- `id`
- `name`
- `summary` - includes goals
- `writing_style` - markdown

### uploads

- `id`
- `text`
- `summary`
- `created_at`
- `client_id` - foreign key to `clients`

### tags

- `id`
- `name` - e.g. transcripts, meeting notes
- `client_id` - foreign key to `clients`

### uploads__tags

Join table for the many-to-many relationship between uploads and tags.

- `upload_id` - foreign key to `uploads`
- `tag_id` - foreign key to `tags`

## Security and grounding principles

- Apply organization and client filters before any vector search.
- Enforce isolation in the database, service layer, scoped credentials, and automated tests - never only in prompts.
- Treat retrieved source text as untrusted data, not instructions for the system.
- Keep source lineage for every segment and insight.
- Require evidence citations for client-specific claims; flag or withhold unsupported claims.
- Use privacy-approved model providers and minimize what is sent to models and logs.
- Keep logs free of raw transcript content and secrets.

## MVP plan

### Phase 1: secure vertical slice

1. Create two client fixtures and prove that a Client A query cannot return Client B content.
2. Build text ingestion with source metadata, deduplication, job status, segmentation, embeddings, and atomic publishing.
3. Build client-filtered semantic retrieval with evidence IDs and short source excerpts.
4. Deliver two writer flows:
   - Find an anecdote or other evidence for a post idea.
   - Review a partial draft against client evidence and identify supported, missing, or unsupported material.
5. Expose a documented API that the product UI can call without direct database access.

### Phase 2: writer experience

1. Add chat-based post enrichment and new-post creation.
2. Add structured extraction for metrics, quotes, anecdotes, voice cues, and image references.
3. Add content briefs, configurable writing-style inputs, and reusable prompt templates.
4. Add an interface for uploading and browsing client context.

### Phase 3: production hardening

1. Add principal-to-client authorization, retention and deletion controls, backups, audit logs, and environment separation.
2. Add evaluation sets for retrieval relevance, citation validity, factual grounding, usefulness, and voice match.
3. Add source adapters such as Fireflies while retaining idempotency and source lineage.
4. Add queues, rate limits, budgets, observability, and provider failover.
5. Add a governed MCP interface over the same service core if agent workflows need it.

## Acceptance criteria

- An authorized user can upload text for a client and see its ingestion job finish or fail safely.
- A writer can retrieve a relevant anecdote, metric, quote, or voice cue and inspect its exact source evidence.
- Draft enrichment clearly separates sourced material from generated suggestions.
- A query for one client cannot expose another client's IDs, excerpts, embeddings, cached results, or logs.
- The UI can use a stable, documented API contract.
- Automated tests cover isolation, ingestion idempotency, retrieval relevance, citation ownership, and the two primary writer workflows.

## Open decisions

- The final organization, client, user, and role model.
- Approved model providers, processing regions, retention terms, and client opt-outs.
- The required human review before a post can be published.
- How writers will rate usefulness, correctness, authenticity, and voice match.
- Whether the primary experience is an embedded product chat, deterministic app screens, or an external private agent.
