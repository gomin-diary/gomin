-- Google OIDC uses the existing member and opaque session model.
alter table public.members alter column password_hash drop not null;
create table public.member_oauth_identities (
 member_id uuid not null references public.members(id) on delete cascade,
 provider text not null check(provider='google'), subject text not null check(subject<>''),
 created_at timestamptz not null default clock_timestamp(),
 primary key(provider,subject), unique(member_id,provider)
);
create table public.oauth_authorization_requests (
 state_digest bytea primary key check(octet_length(state_digest)=32),
 browser_binding_digest bytea not null check(octet_length(browser_binding_digest)=32),
 nonce text not null check(nonce<>''), pkce_verifier_encrypted text not null,
 expires_at timestamptz not null, consumed_at timestamptz
);
create index oauth_requests_browser_idx on public.oauth_authorization_requests(browser_binding_digest);
create index oauth_requests_expiry_idx on public.oauth_authorization_requests(expires_at);
create table public.oauth_pending_actions (
 proof_digest bytea primary key check(octet_length(proof_digest)=32),
 browser_binding_digest bytea not null check(octet_length(browser_binding_digest)=32),
 subject text not null check(subject<>''), email text not null check(email=lower(btrim(email)) and email<>''),
 profile_name text, expires_at timestamptz not null, consumed_at timestamptz
);
create index oauth_pending_browser_idx on public.oauth_pending_actions(browser_binding_digest);
create index oauth_pending_expiry_idx on public.oauth_pending_actions(expires_at);
alter table public.member_oauth_identities enable row level security;
alter table public.oauth_authorization_requests enable row level security;
alter table public.oauth_pending_actions enable row level security;
revoke all on public.member_oauth_identities,public.oauth_authorization_requests,public.oauth_pending_actions from public,anon,authenticated;
grant select,insert,update,delete on public.member_oauth_identities,public.oauth_authorization_requests,public.oauth_pending_actions to service_role;

create function public.gomin_auth_oauth_cleanup() returns jsonb language plpgsql security invoker set search_path='' as $$
begin
 delete from public.oauth_authorization_requests where expires_at<=clock_timestamp() or consumed_at is not null;
 delete from public.oauth_pending_actions where expires_at<=clock_timestamp() or consumed_at is not null;
 return '{}'::jsonb;
end; $$;
create function public.gomin_auth_oauth_begin(p_state bytea,p_binding bytea,p_nonce text,p_verifier text)
returns jsonb language plpgsql security invoker set search_path='' as $$
begin
 perform pg_advisory_xact_lock(hashtextextended(encode(p_binding,'hex'),1));
 delete from public.oauth_authorization_requests where browser_binding_digest=p_binding;
 delete from public.oauth_pending_actions where browser_binding_digest=p_binding;
 insert into public.oauth_authorization_requests values(p_state,p_binding,p_nonce,p_verifier,clock_timestamp()+interval '10 minutes',null);
 return '{}'::jsonb;
end; $$;
create function public.gomin_auth_oauth_consume(p_state bytea,p_binding bytea)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare r public.oauth_authorization_requests%rowtype;
begin
 select * into r from public.oauth_authorization_requests where state_digest=p_state for update;
 if not found or r.browser_binding_digest<>p_binding or r.expires_at<=clock_timestamp() or r.consumed_at is not null then
  return jsonb_build_object('error','OAUTH_REQUEST_INVALID');
 end if;
 update public.oauth_authorization_requests set consumed_at=clock_timestamp(),pkce_verifier_encrypted='' where state_digest=p_state;
 return jsonb_build_object('nonce',r.nonce,'verifier',r.pkce_verifier_encrypted);
end; $$;
create function public.gomin_auth_oauth_login(p_subject text,p_email text,p_session bytea)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare m public.members%rowtype; member_key uuid;
begin
 -- All sub/email writers lock in this order, then the member row.
 perform pg_advisory_xact_lock(hashtextextended(p_subject,2));
 perform pg_advisory_xact_lock(hashtextextended(p_email,0));
 select member_id into member_key from public.member_oauth_identities where provider='google' and subject=p_subject;
 if member_key is not null then
  select * into m from public.members where id=member_key for update;
 else
  select * into m from public.members where email=p_email for update;
  if not found then return jsonb_build_object('new_member',true); end if;
  if exists(select 1 from public.member_oauth_identities where member_id=m.id and provider='google') then
   return jsonb_build_object('error','OAUTH_LINK_CONFLICT');
  end if;
  insert into public.member_oauth_identities(member_id,provider,subject) values(m.id,'google',p_subject);
 end if;
 perform public.create_auth_session(m.id,p_session);
 return jsonb_build_object('id',m.id,'email',m.email,'name',m.name);
exception when unique_violation then return jsonb_build_object('error','OAUTH_LINK_CONFLICT');
end; $$;
create function public.gomin_auth_oauth_pending_begin(p_proof bytea,p_binding bytea,p_subject text,p_email text,p_name text)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare expiry timestamptz:=clock_timestamp()+interval '30 minutes';
begin
 perform pg_advisory_xact_lock(hashtextextended(encode(p_binding,'hex'),1));
 delete from public.oauth_pending_actions where browser_binding_digest=p_binding;
 insert into public.oauth_pending_actions values(p_proof,p_binding,p_subject,p_email,p_name,expiry,null);
 return jsonb_build_object('expires_at',expiry);
end; $$;
create function public.gomin_auth_oauth_pending(p_proof bytea,p_binding bytea)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare r public.oauth_pending_actions%rowtype;
begin
 select * into r from public.oauth_pending_actions where proof_digest=p_proof;
 if not found or r.browser_binding_digest<>p_binding or r.expires_at<=clock_timestamp() or r.consumed_at is not null then
  return jsonb_build_object('error','OAUTH_PROOF_INVALID');
 end if;
 return jsonb_build_object('email',r.email,'profile_name',r.profile_name,'expires_at',r.expires_at);
end; $$;
create function public.gomin_auth_oauth_signup(p_proof bytea,p_binding bytea,p_name text,p_session bytea,
 p_terms text,p_privacy text,p_expected_terms text,p_expected_privacy text)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare r public.oauth_pending_actions%rowtype; member_key uuid;
begin
 select * into r from public.oauth_pending_actions where proof_digest=p_proof for update;
 if not found or r.browser_binding_digest<>p_binding or r.expires_at<=clock_timestamp() or r.consumed_at is not null then
  return jsonb_build_object('error','OAUTH_PROOF_INVALID');
 end if;
 if p_terms<>p_expected_terms or p_privacy<>p_expected_privacy then return jsonb_build_object('error','CONSENT_VERSION_CHANGED'); end if;
 if p_name is null or char_length(btrim(p_name)) not between 1 and 30 then return jsonb_build_object('error','INVALID_NAME'); end if;
 perform pg_advisory_xact_lock(hashtextextended(r.subject,2));
 perform pg_advisory_xact_lock(hashtextextended(r.email,0));
 if exists(select 1 from public.members where email=r.email) then return jsonb_build_object('error','EMAIL_EXISTS'); end if;
 if exists(select 1 from public.member_oauth_identities where provider='google' and subject=r.subject) then return jsonb_build_object('error','OAUTH_LINK_CONFLICT'); end if;
 insert into public.members(email,name,password_hash) values(r.email,btrim(p_name),null) returning id into member_key;
 insert into public.member_oauth_identities(member_id,provider,subject) values(member_key,'google',r.subject);
 insert into public.member_consents(member_id,consent_type,version) values
  (member_key,'terms_of_service',p_terms),(member_key,'privacy_collection',p_privacy);
 perform public.create_auth_session(member_key,p_session);
 update public.oauth_pending_actions set consumed_at=clock_timestamp() where proof_digest=p_proof;
 return jsonb_build_object('id',member_key,'email',r.email,'name',btrim(p_name));
exception when unique_violation then return jsonb_build_object('error','OAUTH_LINK_CONFLICT');
end; $$;
create function public.gomin_auth_oauth_cancel(p_proof bytea,p_binding bytea)
returns jsonb language plpgsql security invoker set search_path='' as $$
begin
 update public.oauth_pending_actions set consumed_at=clock_timestamp() where proof_digest=p_proof and browser_binding_digest=p_binding and consumed_at is null;
 return '{}'::jsonb;
end; $$;
-- Restrict only the functions introduced by this migration.
do $$ declare f record; begin
 for f in select oid::regprocedure as signature from pg_proc where pronamespace='public'::regnamespace and proname like 'gomin_auth_oauth_%' loop
  execute format('revoke all on function %s from public,anon,authenticated',f.signature);
  execute format('grant execute on function %s to service_role',f.signature);
 end loop;
end; $$;
