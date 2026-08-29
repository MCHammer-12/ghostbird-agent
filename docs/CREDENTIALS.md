# Credentials Setup

Configure integrations via environment variables. For production, use FastAPI Cloud secrets (`--secret` flag).

## Clone-per-client checklist

1. Fork or clone this repo for the client
2. Create a Supabase project and connect this GitHub repo (see [DATABASE.md](DATABASE.md))
3. Deploy: `fastapi login && fastapi deploy`
4. Set secrets (below) with `fastapi cloud env set --secret`
5. Redeploy: `fastapi deploy`
6. Share with the client:
   - Base URL: `https://{app}.fastapicloud.dev`
   - API key for automation endpoints (`X-API-Key` header)
   - Webhook URLs as needed

## FastAPI Cloud CLI

```bash
# Non-secret
fastapi cloud env set ENVIRONMENT production

# Secret (encrypted, not visible in dashboard after save)
fastapi cloud env set --secret API_KEY "your-key"
```

Changes take effect on the next deployment. Redeploy after updating secrets.

FastAPI Cloud also supports built-in OAuth integrations for **Neon**, **Redis Cloud**, and **Supabase** — connect these in the dashboard under Integrations to auto-create `DATABASE_URL`, `REDIS_URL`, or Supabase connection env vars.

---

## Core

| Variable | Required | Notes |
|----------|----------|-------|
| `API_KEY` | Yes | Protects `/automations/*` endpoints |
| `ENVIRONMENT` | No | `development` or `production` |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `WEBHOOK_SECRET` | For generic webhooks | Sent as `X-Webhook-Secret` header |

```bash
fastapi cloud env set --secret API_KEY "$(openssl rand -hex 32)"
fastapi cloud env set ENVIRONMENT production
```

---

## LLM (OpenAI, Anthropic, Google)

| Variable | Required | Notes |
|----------|----------|-------|
| `LLM_PROVIDER` | Yes | `openai`, `anthropic`, or `google` |
| `OPENAI_API_KEY` | If provider=openai | [OpenAI API keys](https://platform.openai.com/api-keys) |
| `ANTHROPIC_API_KEY` | If provider=anthropic | [Anthropic console](https://console.anthropic.com/) |
| `GOOGLE_AI_API_KEY` | If provider=google | [Google AI Studio](https://aistudio.google.com/apikey) |

```bash
fastapi cloud env set LLM_PROVIDER openai
fastapi cloud env set --secret OPENAI_API_KEY "sk-..."
```

Endpoint: `POST /automations/llm/complete`

---

## Supabase

| Variable | Required | Notes |
|----------|----------|-------|
| `SUPABASE_URL` | Yes | Project URL from Supabase dashboard |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Service role key (server-side only) |

Install extra locally: `uv sync --extra supabase`

Or use FastAPI Cloud Supabase integration (dashboard → Integrations → Supabase).

```bash
fastapi cloud env set SUPABASE_URL "https://xxx.supabase.co"
fastapi cloud env set --secret SUPABASE_SERVICE_ROLE_KEY "eyJ..."
```

Endpoint: none. The generic `POST /automations/supabase/query` passthrough was
removed — Supabase is reached only by Track 1's retrieval service
(`app/services/retrieval.py`), never by an API caller (docs/TRACKS.md, Rules 1 and 2).

---

## Stripe

| Variable | Required | Notes |
|----------|----------|-------|
| `STRIPE_SECRET_KEY` | For customer API | [Stripe dashboard](https://dashboard.stripe.com/apikeys) |
| `STRIPE_WEBHOOK_SECRET` | For webhooks | From Stripe webhook endpoint settings |

Install extra locally: `uv sync --extra stripe`

```bash
fastapi cloud env set --secret STRIPE_SECRET_KEY "sk_live_..."
fastapi cloud env set --secret STRIPE_WEBHOOK_SECRET "whsec_..."
```

Endpoints:
- `POST /automations/stripe/customer`
- `POST /webhooks/stripe` (configure in Stripe dashboard)

---

## Google (GSuite / Sheets)

| Variable | Required | Notes |
|----------|----------|-------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Yes | Raw JSON or base64-encoded service account key |

1. Create a service account in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Sheets API
3. Share target spreadsheet with the service account email
4. Store the JSON key as a secret

Install extra locally: `uv sync --extra google`

```bash
fastapi cloud env set --secret GOOGLE_SERVICE_ACCOUNT_JSON "$(cat service-account.json)"
```

Endpoint: `POST /automations/google/sheets/append`

---

## Apify

| Variable | Required | Notes |
|----------|----------|-------|
| `APIFY_API_TOKEN` | Yes | [Apify settings](https://console.apify.com/account/integrations) |

```bash
fastapi cloud env set --secret APIFY_API_TOKEN "apify_api_..."
```

Endpoint: `POST /automations/apify/run`

---

## CRM

### HubSpot

| Variable | Required | Notes |
|----------|----------|-------|
| `HUBSPOT_API_KEY` | Yes | Private app access token |

Get from [HubSpot developer settings](https://developers.hubspot.com/).

```bash
fastapi cloud env set --secret HUBSPOT_API_KEY "pat-..."
```

Endpoint: `POST /automations/crm/hubspot/contact`

### Pipedrive

| Variable | Required | Notes |
|----------|----------|-------|
| `PIPEDRIVE_API_TOKEN` | Yes | API token from Pipedrive settings |

### Salesforce

Not included as a working client — use the HubSpot/Pipedrive patterns in `app/integrations/crm.py` as a template.

---

## Email (Resend or SendGrid)

| Variable | Required | Notes |
|----------|----------|-------|
| `RESEND_API_KEY` | One of | [Resend API keys](https://resend.com/api-keys) |
| `SENDGRID_API_KEY` | One of | [SendGrid API keys](https://app.sendgrid.com/settings/api_keys) |
| `EMAIL_FROM` | Yes | Verified sender address |

```bash
fastapi cloud env set --secret RESEND_API_KEY "re_..."
fastapi cloud env set EMAIL_FROM "noreply@yourdomain.com"
```

Endpoint: `POST /automations/email/send`

---

## Local development

```bash
cp .env.example .env
# Edit .env with your keys
uv sync --extra all
uv run dev
```

Check configured integrations: `GET /health/integrations`
