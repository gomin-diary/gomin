-- Retain consumed requests until completion so a newer browser start can cancel
-- callbacks that are still waiting for Google outside the database transaction.
create or replace function public.gomin_auth_oauth_cleanup()
returns jsonb language plpgsql security invoker set search_path='' as $$
begin
 delete from public.oauth_authorization_requests where expires_at<=clock_timestamp();
 delete from public.oauth_pending_actions where expires_at<=clock_timestamp() or consumed_at is not null;
 return '{}'::jsonb;
end; $$;

create function public.gomin_auth_oauth_complete(
 p_state bytea,p_binding bytea,p_subject text,p_email text,p_name text,p_session bytea,p_proof bytea)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare r public.oauth_authorization_requests%rowtype; result jsonb; pending_result jsonb;
begin
 perform pg_advisory_xact_lock(hashtextextended(encode(p_binding,'hex'),1));
 select * into r from public.oauth_authorization_requests where state_digest=p_state for update;
 if not found or r.browser_binding_digest<>p_binding or r.expires_at<=clock_timestamp() or r.consumed_at is null then
  return jsonb_build_object('error','OAUTH_REQUEST_INVALID');
 end if;
 delete from public.oauth_authorization_requests where state_digest=p_state;
 result:=public.gomin_auth_oauth_login(p_subject,p_email,p_session);
 if result ? 'error' then return result; end if;
 if result->>'new_member'='true' then
  pending_result:=public.gomin_auth_oauth_pending_begin(p_proof,p_binding,p_subject,p_email,p_name);
  return jsonb_build_object('new_member',true,'expires_at',pending_result->'expires_at');
 end if;
 return result;
end; $$;
revoke all on function public.gomin_auth_oauth_complete(bytea,bytea,text,text,text,bytea,bytea) from public,anon,authenticated;
grant execute on function public.gomin_auth_oauth_complete(bytea,bytea,text,text,text,bytea,bytea) to service_role;
