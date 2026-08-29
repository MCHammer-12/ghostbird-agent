-- PostgREST connects as service_role. Tables created via SQL migration do not
-- automatically grant privileges to that role unless we do it explicitly.

grant usage on schema public to service_role;

grant select, insert, update, delete on table public.clients to service_role;
grant select, insert, update, delete on table public.uploads to service_role;
grant select, insert, update, delete on table public.tags to service_role;
grant select, insert, update, delete on table public.uploads__tags to service_role;
