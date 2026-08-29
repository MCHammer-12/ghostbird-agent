alter table public.clients
  add column writing_style_prompt_version text;

alter table public.uploads
  add column external_id text,
  add column title text,
  add column source_type text,
  add column purpose text,
  add column captured_at timestamptz,
  add column content_hash text,
  add column ingestion_status text not null default 'queued',
  add constraint uploads_ingestion_status_check check (
    ingestion_status in ('queued', 'processing', 'needs_clarification', 'ignored', 'ready', 'failed', 'superseded')
  ),
  add constraint uploads_client_content_hash_key unique (client_id, content_hash);

alter table public.uploads
  add constraint uploads_id_client_id_key unique (id, client_id);

create or replace function public.start_upload_ingestion(
  p_client_id text,
  p_external_id text,
  p_title text,
  p_source_type text,
  p_text text,
  p_purpose text,
  p_captured_at timestamptz,
  p_metadata jsonb,
  p_content_hash text
)
returns public.uploads
language plpgsql
security invoker
set search_path = ''
as $$
declare
  saved_upload public.uploads;
begin
  update public.uploads
  set ingestion_status = 'superseded'
  where client_id = p_client_id
    and external_id = p_external_id
    and content_hash is distinct from p_content_hash;

  insert into public.uploads (
    client_id,
    external_id,
    title,
    source_type,
    text,
    purpose,
    captured_at,
    metadata,
    content_hash,
    ingestion_status
  )
  values (
    p_client_id,
    p_external_id,
    p_title,
    p_source_type,
    p_text,
    p_purpose,
    p_captured_at,
    p_metadata,
    p_content_hash,
    'processing'
  )
  on conflict (client_id, content_hash) do update
  set external_id = excluded.external_id,
      title = excluded.title,
      source_type = excluded.source_type,
      text = excluded.text,
      purpose = excluded.purpose,
      captured_at = excluded.captured_at,
      metadata = excluded.metadata,
      ingestion_status = 'processing'
  returning * into saved_upload;

  return saved_upload;
end;
$$;

revoke execute on function public.start_upload_ingestion(text, text, text, text, text, text, timestamptz, jsonb, text) from public;
grant execute on function public.start_upload_ingestion(text, text, text, text, text, text, timestamptz, jsonb, text) to service_role;

create table public.metrics (
  id text primary key,
  client_id text not null references public.clients (id) on delete cascade,
  upload_id text not null,
  excerpt text not null,
  source_location text not null,
  scope text not null,
  confidence numeric(4, 3) not null,
  review_status text not null default 'proposed',
  metric_type text not null,
  value_text text not null,
  normalized_value numeric,
  unit text,
  subject text not null,
  context text not null,
  occurred_at text,
  inserted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint metrics_id_format check (id ~ '^met_[0-9a-f]{32}$'),
  constraint metrics_upload_client_fk foreign key (upload_id, client_id)
    references public.uploads (id, client_id) on delete cascade,
  constraint metrics_scope_check check (scope in ('personal', 'client_associated', 'external', 'unknown')),
  constraint metrics_confidence_check check (confidence between 0 and 1),
  constraint metrics_review_status_check check (review_status in ('proposed', 'needs_review', 'approved'))
);

create index metrics_client_id_idx on public.metrics (client_id);
create index metrics_upload_id_idx on public.metrics (upload_id);

create trigger metrics_set_updated_at
  before update on public.metrics
  for each row execute function public.set_updated_at();

create table public.quotes (
  id text primary key,
  client_id text not null references public.clients (id) on delete cascade,
  upload_id text not null,
  excerpt text not null,
  source_location text not null,
  scope text not null,
  confidence numeric(4, 3) not null,
  review_status text not null default 'proposed',
  quote_text text not null,
  speaker text not null,
  speaker_type text not null,
  quote_type text not null,
  context text not null,
  inserted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint quotes_id_format check (id ~ '^quo_[0-9a-f]{32}$'),
  constraint quotes_upload_client_fk foreign key (upload_id, client_id)
    references public.uploads (id, client_id) on delete cascade,
  constraint quotes_scope_check check (scope in ('personal', 'client_associated', 'external', 'unknown')),
  constraint quotes_confidence_check check (confidence between 0 and 1),
  constraint quotes_review_status_check check (review_status in ('proposed', 'needs_review', 'approved')),
  constraint quotes_quote_type_check check (quote_type in ('direct', 'paraphrase', 'remembered'))
);

create index quotes_client_id_idx on public.quotes (client_id);
create index quotes_upload_id_idx on public.quotes (upload_id);

create trigger quotes_set_updated_at
  before update on public.quotes
  for each row execute function public.set_updated_at();

create table public.anecdotes (
  id text primary key,
  client_id text not null references public.clients (id) on delete cascade,
  upload_id text not null,
  excerpt text not null,
  source_location text not null,
  scope text not null,
  confidence numeric(4, 3) not null,
  review_status text not null default 'proposed',
  summary text not null,
  full_story text not null,
  narrator text not null,
  people text[] not null default '{}',
  occurred_at text,
  setup text not null,
  tension text not null,
  action text not null,
  outcome text not null,
  lesson text,
  related_evidence_hints text[] not null default '{}',
  inserted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint anecdotes_id_format check (id ~ '^ane_[0-9a-f]{32}$'),
  constraint anecdotes_upload_client_fk foreign key (upload_id, client_id)
    references public.uploads (id, client_id) on delete cascade,
  constraint anecdotes_scope_check check (scope in ('personal', 'client_associated', 'external', 'unknown')),
  constraint anecdotes_confidence_check check (confidence between 0 and 1),
  constraint anecdotes_review_status_check check (review_status in ('proposed', 'needs_review', 'approved'))
);

create index anecdotes_client_id_idx on public.anecdotes (client_id);
create index anecdotes_upload_id_idx on public.anecdotes (upload_id);

create trigger anecdotes_set_updated_at
  before update on public.anecdotes
  for each row execute function public.set_updated_at();

alter table public.clients enable row level security;
alter table public.uploads enable row level security;
alter table public.tags enable row level security;
alter table public.uploads__tags enable row level security;
alter table public.metrics enable row level security;
alter table public.quotes enable row level security;
alter table public.anecdotes enable row level security;
