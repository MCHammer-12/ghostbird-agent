# FastAPI Cloud Automation Boilerplate

Clone-and-deploy starter for client automations. Secured webhook and action endpoints — no workflow UI, no n8n required.

**One deployment per client.** Set env secrets, deploy, share the API URL + key.

## Quick start

```bash
git clone https://github.com/your-org/fastapi-cloud-base-template.git
cd fastapi-cloud-base-template

uv sync --extra all
cp .env.example .env          # local dev only

fastapi login
fastapi deploy

fastapi cloud env set --secret API_KEY "$(openssl rand -hex 32)"
fastapi cloud env set ENVIRONMENT production
fastapi deploy                  # redeploy after env changes
```

Your app is live at `https://{app}.fastapicloud.dev`. Open `/docs` for interactive API docs.

## What you get

- **Automation endpoints** — call external services via HTTP (`POST /automations/...`)
- **Inbound webhooks** — Stripe and generic webhook receivers
- **Integration stubs** — LLM, Supabase, Stripe, Google Sheets, Apify, HubSpot, email
- **FastAPI Cloud ready** — `fastapi deploy` with zero config

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check |
| GET | `/health/integrations` | None | Which integrations are configured |
| POST | `/automations/llm/complete` | `X-API-Key` | LLM completion |
| POST | `/automations/email/send` | `X-API-Key` | Send email (Resend/SendGrid) |
| POST | `/automations/apify/run` | `X-API-Key` | Run Apify actor |
| POST | `/automations/google/sheets/append` | `X-API-Key` | Append Google Sheet row |
| POST | `/automations/crm/hubspot/contact` | `X-API-Key` | Create HubSpot contact |
| POST | `/automations/stripe/customer` | `X-API-Key` | Create Stripe customer |
| POST | `/webhooks/stripe` | Stripe signature | Inbound Stripe events |
| POST | `/webhooks/generic/{name}` | `X-Webhook-Secret` | Custom inbound webhook |

Example:

```bash
curl -X POST https://your-app.fastapicloud.dev/automations/llm/complete \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize this in one sentence: FastAPI is fast."}'
```

## Documentation

- [Credentials setup](docs/CREDENTIALS.md) — env vars for every integration + FastAPI Cloud CLI
- [Self-hosting](docs/SELF_HOSTING.md) — Linux systemd + Azure App Service/VM

## Add a new automation

1. **Schema** — add request/response models in `app/schemas/automations.py`
2. **Integration** — add a thin client in `app/integrations/`
3. **Route** — add handler in `app/routers/automations.py` with `Depends(verify_api_key)`

Register required env vars in `app/config.py` → `required_for_action()`.

## Local development

```bash
uv sync --extra all
cp .env.example .env
uv run dev
```

Starts on port 8000 by default. If that port is taken, it automatically picks the next available port (8001, 8002, …). Override the starting port with `PORT=9000 uv run dev`.

Visit `/docs` on whatever port the server prints.

## Deploy options

| Method | Command |
|--------|---------|
| Manual | `fastapi deploy` |
| GitHub integration | Connect repo in FastAPI Cloud dashboard |
| GitHub Actions | `fastapi cloud setup-ci` |

## Optional extras

Install integration dependencies as needed:

```bash
uv sync --extra google    # Google Sheets
uv sync --extra stripe    # Stripe
uv sync --extra supabase  # Supabase
uv sync --extra all       # Everything
```

## Project structure

```
app/
├── main.py              # FastAPI app
├── config.py            # Settings + integration helpers
├── dependencies/auth.py # API key + webhook auth
├── routers/             # health, automations, webhooks
├── integrations/        # Thin service clients
└── schemas/             # Pydantic models
docs/
├── CREDENTIALS.md
└── SELF_HOSTING.md
deploy/
├── dev.sh               # Dev server with port fallback
└── setup-secrets.sh     # Interactive secret setup helper
```

## License

MIT — use freely for client work.
