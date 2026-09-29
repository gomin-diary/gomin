-- Verify database access through the key-authenticated Data API.
create or replace function public.health_check()
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$ select true; $$;

revoke all on function public.health_check() from public, anon, authenticated;
grant usage on schema public to service_role;
grant execute on function public.health_check() to service_role;
