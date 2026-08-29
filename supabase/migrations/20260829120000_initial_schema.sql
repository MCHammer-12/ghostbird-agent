create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace function public.prefixed_uuid(prefix text)
returns text
language sql
as $$
  select prefix || '_' || replace(gen_random_uuid()::text, '-', '');
$$;

create table public.clients (
  id text primary key default public.prefixed_uuid('cli'),
  name text not null,
  summary text,
  writing_style text,
  inserted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint clients_id_format check (
    id ~ '^cli_[0-9a-f]{32}$'
  )
);

create trigger clients_set_updated_at
  before update on public.clients
  for each row execute function public.set_updated_at();

create table public.uploads (
  id text primary key default public.prefixed_uuid('upl'),
  text text not null,
  summary text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  client_id text not null references public.clients (id) on delete cascade,
  inserted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uploads_id_format check (
    id ~ '^upl_[0-9a-f]{32}$'
  )
);

create index uploads_client_id_idx on public.uploads (client_id);

create trigger uploads_set_updated_at
  before update on public.uploads
  for each row execute function public.set_updated_at();

create table public.tags (
  id text primary key default public.prefixed_uuid('tag'),
  name text not null,
  client_id text not null references public.clients (id) on delete cascade,
  inserted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (client_id, name),
  constraint tags_id_format check (
    id ~ '^tag_[0-9a-f]{32}$'
  )
);

create index tags_client_id_idx on public.tags (client_id);

create trigger tags_set_updated_at
  before update on public.tags
  for each row execute function public.set_updated_at();

create table public.uploads__tags (
  upload_id text not null references public.uploads (id) on delete cascade,
  tag_id text not null references public.tags (id) on delete cascade,
  inserted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (upload_id, tag_id)
);

create index uploads__tags_tag_id_idx on public.uploads__tags (tag_id);

create trigger uploads__tags_set_updated_at
  before update on public.uploads__tags
  for each row execute function public.set_updated_at();
