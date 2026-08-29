# Database setup and migrations

This repo stores data in **Supabase Postgres**. Schema changes are version-controlled as SQL files in `supabase/migrations/`.

You do not need the Supabase CLI or SQL skills for day-to-day use. Describe what you need, let an agent write the migration file, then push to GitHub.

## Two deploy paths

This repo uses two separate deploy targets. They do not run each other's jobs.

| What | Where it lives | How it deploys |
| --- | --- | --- |
| Database schema | `supabase/migrations/*.sql` | Push to `main` → Supabase GitHub integration |
| API code | `app/` | `fastapi deploy` or FastAPI Cloud GitHub integration |

`fastapi deploy` does **not** run database migrations. Pushing a migration does **not** redeploy the API. After a schema change, redeploy the API only if application code also changed.

## One-time setup (after you fork)

Do this once per Supabase project.

### 1. Create a Supabase project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard).
2. Create a new project.
3. Note the project URL and service role key (Project Settings → API). You will need these for the FastAPI app. See [CREDENTIALS.md](CREDENTIALS.md).

### 2. Connect GitHub

1. In Supabase: **Project Settings → Integrations → GitHub**.
2. Install the Supabase GitHub app and authorize your account.
3. Select **this repo** (your fork).
4. Set the production branch to `main`.
5. Enable **Deploy to production**.

Supabase will apply every migration file in `supabase/migrations/` that has not run yet. The first push after connecting should create all tables from the initial migration.

### 3. Connect the API to Supabase

Set these secrets on FastAPI Cloud (or in `.env` for local dev):

```bash
fastapi cloud env set SUPABASE_URL "https://YOUR-PROJECT.supabase.co"
fastapi cloud env set --secret SUPABASE_SERVICE_ROLE_KEY "eyJ..."
fastapi deploy
```

See [CREDENTIALS.md](CREDENTIALS.md) for full details.

### 4. Confirm the first migration ran

1. In Supabase: **Database → Migrations**. You should see `20260829120000_initial_schema` (or similar) with a success status.
2. In Supabase: **Database → Tables**. You should see `clients`, `uploads`, `tags`, `uploads__tags`, and `posts`.

If the migration failed, open the deployment log in Supabase (Integrations → GitHub → recent deploys) and fix the SQL before pushing again.

## How to change the database shape

### Do

1. Describe the change in plain English (to an agent or your developer).
2. Add a new file under `supabase/migrations/`.
3. Commit and push to `main`.
4. Check Supabase **Database → Migrations** for a green status.

### Do not

- Edit tables in the Supabase **Table Editor** for schema changes. That does not update this repo and will cause drift between environments.
- Edit or delete migration files that already ran in production. Add a new migration instead.
- Run raw SQL in the Supabase SQL editor for schema changes unless you are debugging. Always commit the same SQL as a migration file.

## Migration file naming

Each migration is one SQL file:

```
supabase/migrations/YYYYMMDDHHMMSS_short_description.sql
```

Examples:

- `20260829120000_initial_schema.sql`
- `20260830143000_add_client_logo_url.sql`
- `20260901100000_add_uploads_source_column.sql`

Rules:

- Use UTC timestamp prefix so files sort in run order.
- Use lowercase words separated by underscores in the description.
- One logical change per file when possible.

An agent can generate the timestamp and filename when you ask for a migration.

## Example: ask an agent for a migration

> Add an optional `logo_url` text column to the `clients` table.

An agent should create something like:

```sql
alter table public.clients
  add column logo_url text;
```

in a new file `supabase/migrations/20260830143000_add_client_logo_url.sql`. You commit, push to `main`, and Supabase applies it.

## Verify a migration succeeded

1. Supabase dashboard → **Database → Migrations** → latest file shows success.
2. **Database → Tables** → confirm the new column or table exists.
3. If the API reads the new field, redeploy FastAPI after the migration succeeds.

## If a migration fails

1. Read the error in Supabase → Integrations → GitHub → failed deploy log.
2. Fix the SQL in the migration file (or add a corrective migration if the bad one already partially ran).
3. Push again.

Do not merge broken migrations to `main`. If you use pull requests, enable the Supabase required check so GitHub blocks merges when migration validation fails.

## Optional: preview migrations on a pull request

On the Supabase Pro plan, **Branching** can create a temporary database for each pull request. This lets you test migrations before they hit production. Enable it under **Project Settings → Integrations → GitHub → Automatic branching**.

Free plan: test by pushing to a branch first, or have a developer run the migration against a separate Supabase project.

## Optional: local development with the Supabase CLI

Technical helpers can run migrations locally before push:

```bash
brew install supabase/tap/supabase   # macOS; see supabase.com/docs/guides/cli
supabase login
supabase link --project-ref YOUR-PROJECT-REF
supabase db push                     # apply pending migrations to linked project
```

Local stack (Postgres + Studio on your machine):

```bash
supabase start
supabase db reset                    # replay all migrations from scratch
```

Most fork owners can skip the CLI entirely and rely on GitHub + Supabase dashboard.

## Current schema reference

The live schema is defined by all files in `supabase/migrations/`. The product-level summary is in the [Data model section of README.md](../README.md#data-model).
