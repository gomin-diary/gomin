-- GOMIN-14 / GOMIN-15 / GOMIN-22. Builds on the shared members/session migration.
create table public.member_consents (
    member_id uuid not null references public.members(id) on delete cascade,
    consent_type text not null check (consent_type in ('terms_of_service', 'privacy_collection')),
    version text not null check (version <> ''),
    agreed_at timestamptz not null default clock_timestamp(),
    primary key (member_id, consent_type, version)
);
create table public.email_verifications (
    id uuid primary key,
    email text not null check (email = lower(btrim(email)) and email <> ''),
    code_hmac bytea,
    proof_digest bytea unique,
    status text not null check (status in ('pending','sent','verified','consumed','invalidated','failed')),
    expires_at timestamptz,
    check (code_hmac is null or octet_length(code_hmac) = 32),
    check (proof_digest is null or octet_length(proof_digest) = 32),
    check (
        (status = 'pending' and code_hmac is not null and proof_digest is null and expires_at is null) or
        (status = 'sent' and code_hmac is not null and proof_digest is null and expires_at is not null) or
        (status = 'verified' and code_hmac is null and proof_digest is not null and expires_at is not null) or
        (status in ('consumed','invalidated','failed') and code_hmac is null and proof_digest is null)
    )
);
create index email_verifications_active_email_idx on public.email_verifications(email)
    where status in ('pending','sent','verified');
alter table public.member_consents enable row level security;
alter table public.email_verifications enable row level security;
revoke all on public.member_consents, public.email_verifications from public, anon, authenticated;
grant select, insert, update, delete on public.member_consents, public.email_verifications to service_role;

create function public.gomin_auth_begin_verification(p_id uuid, p_email text, p_code_hmac bytea)
returns jsonb language plpgsql security invoker set search_path = '' as $$
begin
    -- All requests for one email share this lock, including signup and verification.
    perform pg_advisory_xact_lock(hashtextextended(p_email, 0));
    if exists (select 1 from public.members where email = p_email) then
        return jsonb_build_object('error','EMAIL_EXISTS');
    end if;
    update public.email_verifications set status = 'invalidated', code_hmac = null, proof_digest = null
    where email = p_email and status in ('pending','sent','verified');
    insert into public.email_verifications(id,email,code_hmac,status)
    values(p_id,p_email,p_code_hmac,'pending');
    return jsonb_build_object('verification_id',p_id);
end;
$$;

create function public.gomin_auth_finish_delivery(p_id uuid, p_sent boolean)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_expires timestamptz;
begin
    update public.email_verifications
    set status = case when p_sent then 'sent' else 'failed' end,
        code_hmac = case when p_sent then code_hmac else null end,
        expires_at = case when p_sent then clock_timestamp() + interval '3 minutes' else null end
    where id = p_id and status = 'pending'
    returning expires_at into v_expires;
    if not found then return jsonb_build_object('error','VERIFICATION_INVALID'); end if;
    return jsonb_build_object('expires_at',v_expires);
end;
$$;

create function public.gomin_auth_verify_code(p_id uuid, p_email text, p_code_hmac bytea, p_proof_digest bytea)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_row public.email_verifications%rowtype; v_expires timestamptz;
begin
    perform pg_advisory_xact_lock(hashtextextended(p_email, 0));
    select * into v_row from public.email_verifications where id = p_id and email = p_email for update;
    if not found or v_row.status <> 'sent' then
        return jsonb_build_object('error','VERIFICATION_INVALID');
    end if;
    if v_row.expires_at <= clock_timestamp() then return jsonb_build_object('error','CODE_EXPIRED'); end if;
    if v_row.code_hmac <> p_code_hmac then return jsonb_build_object('error','CODE_MISMATCH'); end if;
    v_expires := clock_timestamp() + interval '30 minutes';
    update public.email_verifications set status='verified',code_hmac=null,
        proof_digest=p_proof_digest,expires_at=v_expires where id=p_id;
    return jsonb_build_object('expires_at',v_expires);
end;
$$;

create function public.gomin_auth_signup(
    p_email text, p_name text, p_password_hash text, p_proof_digest bytea, p_session_digest bytea,
    p_terms_version text, p_privacy_version text, p_expected_terms text, p_expected_privacy text
) returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_verification public.email_verifications%rowtype; v_member public.members%rowtype;
begin
    perform pg_advisory_xact_lock(hashtextextended(p_email, 0));
    if p_terms_version <> p_expected_terms or p_privacy_version <> p_expected_privacy then
        return jsonb_build_object('error','CONSENT_VERSION_CHANGED');
    end if;
    select * into v_verification from public.email_verifications
    where email=p_email and proof_digest=p_proof_digest for update;
    if not found or v_verification.status <> 'verified' or v_verification.expires_at <= clock_timestamp() then
        return jsonb_build_object('error','PROOF_INVALID');
    end if;
    if exists (select 1 from public.members where email=p_email) then
        return jsonb_build_object('error','EMAIL_EXISTS');
    end if;
    insert into public.members(email,name,password_hash) values(p_email,p_name,p_password_hash)
    returning * into v_member;
    insert into public.member_consents(member_id,consent_type,version)
    values(v_member.id,'terms_of_service',p_terms_version),(v_member.id,'privacy_collection',p_privacy_version);
    perform public.create_auth_session(v_member.id,p_session_digest);
    update public.email_verifications set status='consumed',proof_digest=null where id=v_verification.id;
    return jsonb_build_object('id',v_member.id,'email',v_member.email,'name',v_member.name);
exception when unique_violation then
    -- This exception block rolls back ALL changes in the attempted signup.
    return jsonb_build_object('error','EMAIL_EXISTS');
end;
$$;

revoke all on function public.gomin_auth_begin_verification(uuid,text,bytea) from public, anon, authenticated;
revoke all on function public.gomin_auth_finish_delivery(uuid,boolean) from public, anon, authenticated;
revoke all on function public.gomin_auth_verify_code(uuid,text,bytea,bytea) from public, anon, authenticated;
revoke all on function public.gomin_auth_signup(text,text,text,bytea,bytea,text,text,text,text) from public, anon, authenticated;
grant execute on function public.gomin_auth_begin_verification(uuid,text,bytea) to service_role;
grant execute on function public.gomin_auth_finish_delivery(uuid,boolean) to service_role;
grant execute on function public.gomin_auth_verify_code(uuid,text,bytea,bytea) to service_role;
grant execute on function public.gomin_auth_signup(text,text,text,bytea,bytea,text,text,text,text) to service_role;
