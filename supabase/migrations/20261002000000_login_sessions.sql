-- GOMIN-16 / GOMIN-25: login's subset of the GOMIN-14 basic ERD.
create table public.members (
    id uuid primary key default gen_random_uuid(),
    email text not null unique check (email = lower(btrim(email)) and email <> ''),
    name varchar(30) not null check (btrim(name) <> ''),
    password_hash text not null,
    created_at timestamptz not null default now()
);

create table public.auth_sessions (
    token_digest bytea primary key check (octet_length(token_digest) = 32),
    member_id uuid not null references public.members(id) on delete cascade,
    expires_at timestamptz not null
);
create index auth_sessions_member_id_idx on public.auth_sessions(member_id);
alter table public.members enable row level security;
alter table public.auth_sessions enable row level security;
revoke all on public.members, public.auth_sessions from public, anon, authenticated;
grant select, insert, update, delete on public.members, public.auth_sessions to service_role;

create function public.create_auth_session(p_member_id uuid, p_digest bytea)
returns void language sql security invoker set search_path = '' as $$
    insert into public.auth_sessions(token_digest, member_id, expires_at)
    values (p_digest, p_member_id, clock_timestamp() + interval '7 days');
$$;

-- Lock before checking expiration, then UPDATE only; a concurrent logout can
-- never recreate a deleted session. Use the database clock for both operations.
create function public.renew_auth_session(p_digest bytea)
returns table(id uuid, email text, name varchar)
language plpgsql security invoker set search_path = '' as $$
declare
    v_session public.auth_sessions%rowtype;
begin
    select s.* into v_session from public.auth_sessions s
    where s.token_digest = p_digest for update;
    if not found or v_session.expires_at <= clock_timestamp() then
        return;
    end if;
    update public.auth_sessions s
    set expires_at = clock_timestamp() + interval '7 days'
    where s.token_digest = p_digest;
    return query select m.id, m.email, m.name from public.members m
    where m.id = v_session.member_id;
end;
$$;
revoke all on function public.create_auth_session(uuid, bytea) from public, anon, authenticated;
revoke all on function public.renew_auth_session(bytea) from public, anon, authenticated;
grant execute on function public.create_auth_session(uuid, bytea) to service_role;
grant execute on function public.renew_auth_session(bytea) to service_role;
