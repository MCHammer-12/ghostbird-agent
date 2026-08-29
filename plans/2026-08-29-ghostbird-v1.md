# Plan: Ghostbird Agent V1
**Status:** In Progress
**Created:** 2026-08-29

## Context

Build the first working agent layer against the existing FastAPI template and synthetic client corpus. Extraction agents may write their own bounded record types directly. The Voice Profile Agent owns one Markdown profile per client rather than a collection of voice-observation rows.

## Approach

- Define stable source, extraction, evidence, voice-profile, enrichment, and ideation contracts.
- Store each prompt as a versioned Markdown file.
- Give each extraction agent a narrow repository write method.
- Keep model-produced client and source identity out of the write path; the service supplies both from the authorized request.
- Use an in-memory repository for local tests and a Supabase repository for production integration.
- Create a labeled Marisol evaluation set and exercise the complete orchestration path with recorded structured model responses.

## Alternatives Considered

- A separate voice-observation agent and voice-profile agent was rejected for V1. One agent updates one Markdown profile.
- One orchestrator-owned batch write was rejected. Each extractor writes its own idempotent records directly.
- Arbitrary database access for agents was rejected. Each agent receives only its specific write contract.

## Sections

- [ ] Agent contracts and prompts
- [ ] Repositories and orchestration
- [ ] FastAPI routes
- [ ] Marisol evaluation fixtures and runner
- [ ] Documentation and verification

## Verification

- All extraction outputs validate against typed schemas.
- Reprocessing a source does not duplicate evidence.
- A clarification-required upload does not publish extracted evidence.
- Client identity is supplied by code and cannot be changed by model output.
- Voice updates overwrite one Markdown profile per client.
- Enrichment and ideation outputs cite evidence IDs that belong to the selected client.
- The full test suite passes.
