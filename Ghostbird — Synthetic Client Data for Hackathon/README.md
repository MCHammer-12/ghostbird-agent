# Ghostbird — Synthetic Client Content Data

**100% fictional.** Every client, person, company, story, number, and email
below was invented for app development / testing purposes. Nothing here
represents a real Ghostbird client, call, or message. This set was put
together as sample data for testing an ingestion pipeline against
realistic-looking client content — 3 fictional clients, 5 call transcripts,
10 emails, matching the shape of what Fireflies and Gmail actually return.

## What's in here

```
manifest.json          index of every client, transcript, and email thread
transcripts/*.json      one file per call, shaped like the Fireflies transcript API
emails/*.json           one file per email thread, shaped like the Gmail thread API
```

Every JSON file also carries a `_synthetic_data_notice` and `_client_ref`
field so it's unmistakable in a database or vector store that this is sample
data, not a real client record.

## The three fictional clients

| Client | Company | Industry | Calls | Cadence |
|---|---|---|---|---|
| Marisol Vance | Vance & Kinder Supply Co. | Industrial fasteners & hardware distribution (B2B) | 2 | Monthly content interview |
| Priya Chandrasekhar | Bloom & Bar Aesthetics | Boutique med-spa / beauty franchise | 2 | Monthly content interview |
| Desmond Okafor | Ridgeline Custom Builds | Custom home building / design-build | 1 | Quarterly content interview |

Full bios are in `manifest.json` under `clients`.

## Transcript shape (`transcripts/*.json`)

Mirrors the fields returned by the Fireflies transcript API: `id`, `title`,
`dateString`, `duration` (minutes), `organizerEmail`, `meetingLink`,
`meetingAttendees`, `participants`, `meetingInfo`, a `summary` block
(`short_summary`, `keywords`, `action_items`), and a `sentences` array of
`{speaker_name, start_time, end_time, text}` (seconds).

## Email shape (`emails/*.json`)

Mirrors the fields returned by the Gmail thread API: `threadId`, `subject`,
and a `messages` array of `{id, date, sender, toRecipients, ccRecipients,
labelIds, plaintext_body, snippet}`.

## Why the content looks the way it does

Each client's calls and emails follow the same real-world pattern Ghostbird's
actual content interviews follow: a personal/business update, a story mined
in detail (with a follow-up question or two), a specific lesson or metric,
and a short list of resulting post ideas with next steps and asset requests
— then a follow-up email thread where drafts get sent for review and the
client leaves notes or approves. The goal was structural and tonal realism
(so an ingestion or RAG pipeline sees data shaped like the real thing), not
literal length — these calls run shorter than a full 45–90 minute real
interview.

Questions on the format, or need it reshaped for how you're ingesting it?
Just reply to the email this came with.
