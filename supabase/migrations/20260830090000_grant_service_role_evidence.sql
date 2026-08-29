-- 20260829130000_grant_service_role.sql granted the CRUD tables to service_role,
-- but 20260829220000_add_agent_evidence.sql added metrics, quotes, and anecdotes
-- without matching grants. PostgREST connects as service_role, so without these
-- the ingestion agents fail to publish evidence.

grant select, insert, update, delete on table public.metrics to service_role;
grant select, insert, update, delete on table public.quotes to service_role;
grant select, insert, update, delete on table public.anecdotes to service_role;
