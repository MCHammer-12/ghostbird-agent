# Product decisions

## Adaptive clarification during ingestion

The ingestion service should parse an upload before publishing extracted evidence. A clarification agent asks questions only when missing or ambiguous information would materially affect attribution, client relevance, or safe use.

Examples:

- What is the purpose of this upload for this client?
- Who are the speakers?
- Is this a personal client story, something associated with the client, or external inspiration?
- May quoted material be attributed to the named speaker?

Ask at most three high-value questions in one batch. The user may skip them. Skipped or unresolved information remains `unknown` or `needs_review` and cannot be presented as a verified client fact or direct client quote.

Do not interrupt clear uploads. If the client, source type, speakers, and purpose can be inferred confidently, ingestion should continue without questions.

## Voice Profile Agent

Use one Voice Profile Agent alongside the metric, quote, and anecdote agents. It maintains one complete Markdown document in `clients.writing_style`, replacing that value whenever new approved voice evidence is incorporated. Do not create separate voice-observation rows or a second profile-synthesis agent.

The Markdown profile contains evidence-backed observations about vocabulary, cadence, directness, humor, sentence structure, storytelling, formatting, hooks, closers, and client corrections.

Voice inputs should be weighted by what they are best able to prove:

- Call transcripts and audio-derived transcripts are strongest for natural phrasing, vocabulary, cadence, humor, opinions, and storytelling.
- Approved or published LinkedIn posts are strongest for channel-specific structure, formatting, hooks, length, punctuation, and polish.
- Client edits are strongest for hard preferences, boundaries, and negative rules.
- AI-generated drafts, third-party writing, and unverified material are not voice evidence unless explicitly approved by the client.

The Markdown profile must retain supporting evidence references and distinguish spoken voice from approved written voice.

## Configurable writing workflow

Ghostbird can provide a useful default workflow: retrieve evidence, propose distinct angles or hooks, let the writer select a direction, draft, and validate. This sequence should be configurable rather than hardcoded because the agency may already have its own ideation, framework, review, and approval process.

The retrieval and evidence layer is the durable product. Workflow recipes, prompts, framework tags, and review steps should be replaceable without changing the underlying client context store.

## Human review

Generated posts and extracted voice rules require human review before publication or promotion into an authoritative client profile. The system supports the ghostwriter's process; it does not silently replace agency judgment.

## Context breadcrumbs

Every output that uses a client-specific metric, quote, anecdote, voice rule, or other evidence must return stable evidence references at the claim or suggestion level. The application turns those references into clickable breadcrumbs; the model must not invent source URLs.

A breadcrumb should open an evidence drawer with:

- The exact supporting excerpt
- Enough surrounding context to understand the excerpt
- Source title, type, and date
- Speaker or author
- Transcript timestamp, page, or character range
- Personal, client-associated, or external classification
- Related metrics, quotes, anecdotes, or voice observations
- A link to open the authorized source at the relevant location

The default output stays compact. Writers can progressively expand from the inline reference, to the evidence drawer, to the complete source.

Composite claims may reference multiple evidence records. If an output cannot provide a valid evidence reference for a client-specific claim, it must label the claim as an unsupported suggestion or omit it.
